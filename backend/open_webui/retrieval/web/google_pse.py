import logging
from typing import Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from open_webui.retrieval.web.main import SearchResult, get_filtered_results
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])

# Default timeout for Google PSE API requests (in seconds)
DEFAULT_TIMEOUT = 10


def _fetch_page(api_key: str, search_engine_id: str, query: str, start_index: int, num_results: int, timeout: int = DEFAULT_TIMEOUT) -> list[dict]:
    """Fetch a single page of results from Google PSE API.
    
    Args:
        api_key: Google PSE API key
        search_engine_id: Google PSE Engine ID
        query: Search query
        start_index: Starting index for results (1-based)
        num_results: Number of results to fetch (max 10)
        timeout: Request timeout in seconds
        
    Returns:
        List of result items from the API
    """
    url = "https://www.googleapis.com/customsearch/v1"
    headers = {"Content-Type": "application/json"}
    params = {
        "cx": search_engine_id,
        "q": query,
        "key": api_key,
        "num": num_results,
        "start": start_index,
    }
    
    try:
        log.debug(f"Fetching Google PSE page: start={start_index}, num={num_results}")
        response = requests.get(url, headers=headers, params=params, timeout=timeout)
        response.raise_for_status()
        json_response = response.json()
        results = json_response.get("items", [])
        log.debug(f"Fetched {len(results)} results from page starting at {start_index}")
        return results
    except requests.exceptions.Timeout:
        log.error(f"Google PSE API timeout after {timeout}s for start_index={start_index}")
        return []
    except Exception as e:
        log.error(f"Error fetching Google PSE page at start_index={start_index}: {e}")
        raise


def search_google_pse(
    api_key: str,
    search_engine_id: str,
    query: str,
    count: int,
    filter_list: Optional[list[str]] = None,
    timeout: int = DEFAULT_TIMEOUT,
    parallel_requests: bool = True,
) -> list[SearchResult]:
    """Search using Google's Programmable Search Engine API and return the results as a list of SearchResult objects.
    Handles pagination for counts greater than 10 with optional parallel fetching.

    Args:
        api_key (str): A Programmable Search Engine API key
        search_engine_id (str): A Programmable Search Engine ID
        query (str): The query to search for
        count (int): The number of results to return (max 100, as PSE max results per query is 10 and max page is 10)
        filter_list (Optional[list[str]], optional): A list of keywords to filter out from results. Defaults to None.
        timeout (int): Request timeout in seconds. Defaults to 10.
        parallel_requests (bool): Whether to fetch pages in parallel. Defaults to True.

    Returns:
        list[SearchResult]: A list of SearchResult objects.
    """
    log.info(f"Starting Google PSE search for query: '{query}', requesting {count} results")
    
    # Calculate pagination parameters
    pages_needed = (count + 9) // 10  # Round up to nearest page
    pages_needed = min(pages_needed, 10)  # Google PSE max is 10 pages (100 results)
    
    all_results = []
    
    if parallel_requests and pages_needed > 1:
        # Parallel fetching for multiple pages
        log.debug(f"Fetching {pages_needed} pages in parallel")
        
        with ThreadPoolExecutor(max_workers=min(pages_needed, 5)) as executor:
            # Submit all page requests
            future_to_page = {}
            for page_num in range(pages_needed):
                start_index = page_num * 10 + 1
                num_results_this_page = min(10, count - page_num * 10)
                
                future = executor.submit(
                    _fetch_page,
                    api_key,
                    search_engine_id,
                    query,
                    start_index,
                    num_results_this_page,
                    timeout
                )
                future_to_page[future] = page_num
            
            # Collect results in order
            page_results = [None] * pages_needed
            for future in as_completed(future_to_page):
                page_num = future_to_page[future]
                try:
                    results = future.result()
                    page_results[page_num] = results
                except Exception as e:
                    log.error(f"Error fetching page {page_num}: {e}")
                    page_results[page_num] = []
            
            # Flatten results
            for results in page_results:
                if results:
                    all_results.extend(results)
    else:
        # Sequential fetching (original behavior)
        log.debug(f"Fetching {pages_needed} pages sequentially")
        start_index = 1
        remaining_count = count
        
        while remaining_count > 0 and start_index <= 91:  # Max start index is 91 (for 100 results)
            num_results_this_page = min(remaining_count, 10)
            results = _fetch_page(api_key, search_engine_id, query, start_index, num_results_this_page, timeout)
            
            if results:
                all_results.extend(results)
                remaining_count -= len(results)
                start_index += 10
            else:
                break  # No more results
    
    log.info(f"Google PSE search completed: fetched {len(all_results)} results")
    
    if filter_list:
        original_count = len(all_results)
        all_results = get_filtered_results(all_results, filter_list)
        log.debug(f"Filtered results: {original_count} -> {len(all_results)}")

    return [
        SearchResult(
            link=result["link"],
            title=result.get("title"),
            snippet=result.get("snippet"),
        )
        for result in all_results
    ]
