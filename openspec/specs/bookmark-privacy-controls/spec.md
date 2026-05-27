# bookmark-privacy-controls Specification

## ADDED Requirements

### Requirement: Per-bookmark visibility
Every bookmark SHALL have a `visibility` field with values `public` or `private`. Only public bookmarks SHALL be visible via federation or public profile pages.

#### Scenario: Bookmark created with explicit visibility
- GIVEN a user creating a new bookmark
- WHEN visibility is explicitly set to `public`
- THEN the bookmark is visible to followers and on public profile
- WHEN visibility is explicitly set to `private`
- THEN the bookmark is visible only to the owning user

#### Scenario: API respects visibility
- GIVEN a user's private bookmarks
- WHEN a remote ActivityPub request attempts to fetch the bookmark object
- THEN a 403 Forbidden or 404 Not Found response is returned

### Requirement: Default visibility setting
Every user SHALL have a configurable default visibility for new bookmarks, stored in their profile. The default SHALL be `private` for new registrations.

#### Scenario: New user has private default
- GIVEN a new user registration
- WHEN the user creates their first bookmark without specifying visibility
- THEN the bookmark visibility defaults to `private`

#### Scenario: User changes default
- GIVEN a registered user
- WHEN the user updates their default bookmark visibility to `public`
- THEN all subsequent bookmarks created without explicit visibility default to `public`

### Requirement: Visibility enforcement in views
All bookmark listing views and the public API SHALL filter bookmarks by visibility based on the requesting user's relationship to the owner. Only the owner sees their private bookmarks.

#### Scenario: Owner sees all bookmarks
- GIVEN user `alice` viewing her own bookmarks
- WHEN any bookmark listing page is loaded
- THEN both public and private bookmarks are shown

#### Scenario: Non-owner sees only public bookmarks
- GIVEN user `bob` viewing `alice`'s profile/bookmarks
- WHEN `bob` is not `alice`
- THEN only bookmarks with `visibility: public` are shown

#### Scenario: Unauthenticated visitor sees public bookmarks
- GIVEN an unauthenticated visitor on `alice`'s public profile
- WHEN the page loads
- THEN only bookmarks with `visibility: public` are shown

### Requirement: Visibility indicator in UI
Each bookmark card SHALL display a visual indicator of its visibility (public/private icon or label) to the owning user.

#### Scenario: Visibility shown to owner
- GIVEN user `alice` viewing her own bookmark list
- WHEN a bookmark is public
- THEN a globe/public icon is shown
- WHEN a bookmark is private
- THEN a lock/private icon is shown

#### Scenario: No visibility indicator for non-owner
- GIVEN user `bob` viewing `alice`'s bookmarks
- WHEN viewing public bookmarks
- THEN no visibility indicator is shown (all visible bookmarks are public by definition to bob)