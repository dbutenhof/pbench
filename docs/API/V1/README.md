# Pbench Server V1 API documentation

The documents in this set describe the APIs supported by the Pbench 1.0 Server.

## Discovering the Pbench Server API

Once you know the hostname of a Pbench Server, you can ask for the API
configuration using the [endpoints](endpoints.md) API. This will report the
server's version and a list of all API end points supported by the server.

## Pbench Server configuration settings

Some aspects of Pbench Server operation can be controlled by a user holding the
`ADMIN` [role](../access_model.md) through the
[server configuration](./server_config.md) API, including disabling the Pbench
Server API while the server is undergoing maintenance and setting a banner
message accessible to clients.

## Pbench Server resources

### Datasets

The dataset resource encompasses everything the Pbench Server knows about a
performance run captured by the Pbench Agent through a "dataset tarball". This
includes the physical files transferred from the agent along with all backend
databases maintained by the server.

The API identifies a dataset using the dataset resource ID, which is a hex
representing a checksum hash of the dataset tarball. This ID can't change during
the life of the dataset.

When a dataset is deleted, all data maintained by the server associated with that
dataset resource ID is deleted, including backend database records, unpacked file
artifacts, and the archived tarball. The resource ID becomes invalid subsequently
unless a new dataset is created with the same checksum value. (This is highly
unlikely, unless the same Pbench Agent tarball is uploaded again.)

### Users

User resources are identified by a `username` property, which must be unique
among all users registered on the Pbench Server. The user resource has a
"user profile" that includes first and last name, and a contact email.

A user resource is the "owner" of each [dataset](#datasets) managed by the
Pbench Server. If a user is deleted, then any datasets owned by that user
become orphaned; datasets with PUBLIC access are still accessible to other
users, and PRIVATE datasets are accessible through the `ADMIN` user role (see
[access model](../access_model.md)).

### Metadata

Metadata resources are secondary resources tied to a dataset resource and, for
the `user` namespace also to a user resource. Metadata resources are key/value
pairs, as described in [metadata](../metadata.md).

The lifetime of a metadata resource is bounded by the lifetime of the dataset
resource ID. That is, when a dataset is deleted, all metadata associated with
that dataset is also deleted. If a user is deleted, then all `user` namespace
metadata associated with that user (for any dataset) is also deleted.

Although `user` namespace metadata can be associated with any dataset to which
the authenticated user has READ access, those metadata keys will become
unreachable if the user's access to the associated dataset changes to remove
READ access. For example, if a PUBLIC access dataset owned by a different user
is made PRIVATE, or if the user relies on a role or group (see
[access model](../access_model.md)) to READ the dataset and that privilege is
removed. In this case, however, the metadata values remain, and will become
visible again if READ access is restored.

## Login and registration

You can register a new user (depending on the administration policy of the
server) using the [register](register.md) API. If this succeeds, you can log in
using the new username and password.

You can log in as a registered user by calling the [login](login.md) API, which
returns a bearer schema authentication token that should be provided to
subsequent API calls using the `authorization` header.

You can log out an active authentication token by passing it as the
`authorization` header to the [logout](logout.md) API.

While logged in, you can retrieve (`GET`) and modify (`PUT`) your user profile
through the [user](user.md) API.

## Dataset metadata

You can read a more complete specification of Pbench Server metadata at
[metadata](../metadata.md).

When a dataset is first processed, the Pbench Server will populate basic
metadata, including the creation timestamp, the owner of the dataset (the user
associated with the authorization token given to the Pbench Agent
`pbench-results-move` command), and the full contents of the dataset's
`metadata.log` file inside the dataset tarball. The Pbench Server will also
calculate a default deletion date for the dataset based on the owner's
retention policy and the server administrator's retention policy.

Clients can also set arbitrary metadata through the `dashboard` and `user`
metadata namespaces. The `dashboard` namespace can only be modified by the
owner of the dataset, and is visible to anyone with read access to the dataset.
The `user` namespace is private to each authenticated user, and even if you
don't own a dataset you can set your own private `user` metadata to help you
categorize that dataset and to find it again.

The primary dataset `resource_id` is the computed MD5 of the dataset tarball.
This is generated by the agent, and checked on the server side to ensure data
consistency.

## Discovering accessible datasets

The datasets accessible by a client are limited by the dataset access controls
and the client's authorization. Any client can read all "public" datasets, but
only the owning user can access "private" datasets.

You can determine the datasets you're allowed to view using the [list](list.md)
API. This will return the resource name, the formal resource ID, and selected
metadata for each dataset the authenticated user is allowed to read. You can
filter the datasets you want listed by date range, owning user, or access
policy.

It may sometimes be convenient to know the date range of those datasets in
advance, for example to initialize a date picker. You can do this by calling
the [daterange](daterange.md) API to determine the range of dataset creation
dates accessible to the authenticated client.

## Discovering dataset details

To get the details of the dataset's run configuration, in addition to specified
server metadata, you can use the [detail](detail.md) API. This returns the
resource ID of each selected dataset, along with selectable metadata providing
information about the system configuration and tool configuration for the
dataset.

## Managing a dataset

You can control the visibility (access policy) for a dataset that you own by
using the [publish](publish.md) API. You can make each dataset "public"
(readable to everyone) or "private" (readable only to you).

To delete a dataset you own, use [delete](delete.md).

## Accessing dataset inventory

The Pbench Agent code uploads a dataset to the Pbench Server in the form of a
tarball with a carefully designed format. That tarball contains a directory
structure which the Pbench Server uses to index and expose details collected by
the Pbench Agent during the course of a Pbench benchmark run.

While there are many ways for a client to access the metrics and metadata
associated with a dataset, a client can also directly access the dataset
tarball inventory.

The [contents](contents.md) API exposes the directory hierarchy within the
tarball, from the root directory `/` through the leaf files. A client can
discover the entire hierarchical content of the dataset tarball by iterating
through the `directories` list of each
[directory object](contents.md#directory-object).

The [inventory](inventory.md) API returns the raw byte stream of any regular
file within the directory hierarchy, including log files, postprocessed JSON
files, and benchmark result text files.

### Example

```
    def directory(request, url: str, name: str = "/", level: int = 0):
        ls = request.get(url).get_json()
        print(f"{'  '*level}{name}")
        for d in ls.directories:
            directory(request, level + 1, d.name, d.url)
        for f in ls.files:
            print(f"{'  '*(level+1)}{f.name})
            bytes = request.get(f.url)
            # display byte stream:
            # inline on terminal doesn't really make sense

    directory(request, "http://host.example.com/api/v1/contents/<dataset>/")
```