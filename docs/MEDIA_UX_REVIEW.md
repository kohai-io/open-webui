# Media UX review

Reviewed 12 September 2026 against the local v0.11.3 stage instance at desktop and
390px phone widths. Live checks covered the two existing images, filename search,
preview open/close, and opening then cancelling deletion. Pagination and failure
behaviour were also reviewed in the component and existing mocked tests. Live
video/audio streaming was not exercised.

## Sidebar correction

Home and Media retained the old sidebar styling after the upstream upgrade.
Measured at the default desktop text size, their rows were 36px high with 18px
icons and 14px labels; the upstream rows were 32px, 16px and 13px respectively.
Their labels also started 11px farther to the right.

The custom links now share a small `NavigationLink.svelte` component matching the
v0.11.3 expanded and collapsed sidebar styles. Both expose the selected route via
`aria-current` and use upstream selected-page colours, including high contrast.
Home remains conditional on the Welcome feature flag. Modified clicks retain
normal browser link behaviour.

Validation: production frontend build, 15 focused unit tests and all four existing
mocked Media browser tests passed. Browser measurements confirmed that Home, Media
and the upstream links now have identical 32px rows, 16px icons, 13px labels and
36px label start positions. Collapsed links measure 32px square with 16px icons;
Home/Media navigation and selected-route changes were checked in an isolated UI
fixture. This source correction has not yet been included in a new container image.

## Recommended Media changes

| Priority | Finding                                                                                                                                                                  | Proposed change                                                                                                                                                                                                                                               |
| -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| First    | Both existing images are named `generated-image.png`. Cards and preview titles provide no date, type or size to distinguish them.                                        | Show file type, creation date and size beneath the filename, using existing Files API metadata. Omit unavailable values. Keep the full filename accessible in preview.                                                                                        |
| First    | A search with no matches still says “Media files loaded: 2”. Search and type filters cover only loaded files; later media can be hidden behind pages of non-media files. | Show “0 of 2 loaded files” while filtering, label the search scope clearly and put the partial-library notice on its own line. Add Clear filters and a contextual Load more action to the empty state. Distinguish an empty library from no matching results. |
| First    | Every card gives Delete equal prominence to Download. The confirmation warns about affected chats but gives no filename or thumbnail.                                    | Put Delete in a labelled overflow menu. Identify the selected file in the confirmation, with a thumbnail and available metadata for duplicate names. Retain the warning that deletion also removes access from chats.                                         |
| Next     | Preview supports viewing and closing only. To download or inspect another image, users must close it and find another card.                                              | Add Download, previous/next controls and position within the filtered results. Support keyboard arrows and Escape. Offer an original-size image view and file details.                                                                                        |
| Next     | The fixed 16:9 thumbnail area makes portrait artwork small. Video and audio use the same generic photo icon.                                                             | Trial square image tiles with contained, uncropped previews. Use distinct video/audio icons and clear type labels. Keep playback on demand.                                                                                                                   |
| Next     | Refresh clears the current gallery before its replacement request succeeds, and returns a paginated view to page one.                                                    | Keep the existing gallery visible until refresh succeeds; retain filters and announce any reset of loaded results. On failure, keep the previous content with an inline Retry action.                                                                         |
| Polish   | Card action targets are small on phones, although the grid and preview fit the viewport.                                                                                 | Increase touch targets and check keyboard focus visibility on every card action and preview control.                                                                                                                                                          |

## What already works

- The responsive grid fits phone width and the preview contains portrait images.
- Search and type controls are compact, with an explicit Load more operation.
- Lazy image loading and on-demand video/audio playback avoid eagerly loading the
  whole library.
- Deletion requires confirmation, warns about chat access, and restarts pagination
  to avoid skipping files after upstream offsets move.

## Suggested first implementation

Implement card metadata, clearer filtered counts and empty states, then the action
menu and identified deletion confirmation. Follow with preview browsing and
download controls. These can remain within the existing custom Media feature and
Files API.

Full-library search/sorting and “Open source chat” need a separate API and access
review. Do not imply those capabilities from the current loaded-file filter or
infer a source chat from a filename.
