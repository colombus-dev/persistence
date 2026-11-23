"""Application service layer for the persistence GraphQL API.

Domain creation/defaulting rules that used to live inline in GraphQL mutation
resolvers, extracted so they are reachable without the Strawberry schema and
unit-testable in isolation. Resolvers are thin delegates over these functions.
"""
