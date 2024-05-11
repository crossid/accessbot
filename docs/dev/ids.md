# IDs

- We use nanoid for better readablity.

# Workspace IDs

Workspace ids are used in multiple services to segment data between tenants.
Some of the services are not accepting various characters (e.g., Azure's key vault does not accept `_` char while SQLite tables cannot contain `-` char)

Decisions:

- Agreed to avoid maintaining another _unique_name_ property as it's annoying to ask it from the user.
- Whenever possible maintain a convertion table between the unique name on the service and the workspace_id.
- In cases convertion table is not possible, convert one char to another dynamically (collision-wise it's a bit risky)
