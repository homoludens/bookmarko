# fediverse-public-bookmark-page Specification

## ADDED Requirements

### Requirement: Public user profile page
Every user SHALL have a public profile page at `/user/<username>` displaying their bio, follower/following counts, and public bookmarks. This page SHALL be accessible without authentication.

#### Scenario: View public profile
- GIVEN a registered user with public bookmarks
- WHEN an unauthenticated visitor navigates to `/user/<username>`
- THEN the page displays the username, bio, follower/following counts, and paginated public bookmarks
- AND a "Follow" button is shown for logged-in users who aren't already following

#### Scenario: Actor profile with content negotiation
- WHEN a request is made to `/user/<username>` with `Accept: application/activity+json`
- THEN the response is the ActivityPub Actor JSON with `type: Person`
- WHEN a request is made with `Accept: text/html`
- THEN the response is the HTML user profile page

### Requirement: Public bookmark as ActivityPub Object
Each public bookmark SHALL have an ActivityPub Object representation accessible at a canonical URL. The object type SHALL be `Article` or `Note` with the bookmark title, URL, description, and tags.

#### Scenario: Fetch bookmark as ActivityPub Object
- WHEN a request with `Accept: application/activity+json` is made to a public bookmark's URL
- THEN the response includes `@context`, `id`, `type`, `attributedTo` (actor URL), `name` (title), `content` (description), `url` (the bookmark's external URL), `tag` (tags array), and `published`
- WHEN the bookmark is private
- THEN a 404 is returned

#### Scenario: Bookmark object accessible via ID
- WHEN a remote instance fetches `/api/v1/activitypub/objects/<bookmark-id>`
- THEN the ActivityPub Object JSON for that bookmark is returned
- AND private bookmarks return 404

### Requirement: Public bookmark listing as Collection
A user's public bookmarks SHALL be accessible as a paginated ActivityPub Collection at the actor's outbox or a dedicated bookmark collection endpoint.

#### Scenario: Actor outbox shows public bookmarks
- WHEN a request is made to a user's outbox with `Accept: application/activity+json`
- THEN the response is an OrderedCollection of Create activities
- AND each activity's `object` is the bookmark Object
- AND only public bookmarks are included