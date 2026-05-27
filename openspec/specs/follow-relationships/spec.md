# follow-relationships Specification

## ADDED Requirements

### Requirement: Same-instance follow (auto-accept)
A user SHALL be able to follow another user on the same instance. Follows SHALL be auto-accepted — no pending/approval workflow. The follow relationship is established immediately.

#### Scenario: User follows another user
- GIVEN two users `alice` and `bob` on the same instance
- WHEN `alice` follows `bob`
- THEN a Follow record is created with status `accepted`
- AND `alice` is added to `bob`'s followers collection
- AND `bob` is added to `alice`'s following collection

#### Scenario: User unfollows
- GIVEN an existing follow relationship from `alice` to `bob`
- WHEN `alice` unfollows `bob`
- THEN the follow record is deleted
- AND `alice` is removed from `bob`'s followers collection
- AND `bob` is removed from `alice`'s following collection

### Requirement: Follower/following collections
Every user SHALL have ActivityPub-compatible followers and following collections, served as Collection or OrderedCollection pages.

#### Scenario: View followers collection
- WHEN a request is made to a user's followers URL
- THEN the response is an ActivityPub Collection with `totalItems` and paginated `items`
- AND the response content type is `application/activity+json` for ActivityPub clients

#### Scenario: View following collection
- WHEN a request is made to a user's following URL
- THEN the response is an ActivityPub Collection with `totalItems` and paginated `items`
- AND items are ordered by follow date (most recent first)

### Requirement: User-facing follow management UI
Users SHALL have a web UI to view their followers, who they follow, follow/unfollow other users.

#### Scenario: Follow button on user profile
- GIVEN user `alice` viewing `bob`'s profile
- WHEN `alice` is not currently following `bob`
- THEN a "Follow" button is displayed
- WHEN `alice` clicks "Follow"
- THEN the follow relationship is established immediately

#### Scenario: Unfollow button on user profile
- GIVEN `alice` is following `bob`
- WHEN `alice` views `bob`'s profile
- THEN an "Unfollow" button is displayed
- WHEN `alice` clicks "Unfollow"
- THEN `alice` is removed from `bob`'s followers