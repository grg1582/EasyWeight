"""EasyWeight backend API.

    config     settings from environment variables
    db         database engine and sessions
    models     the database tables (SQLAlchemy)
    schemas    request and response shapes (Pydantic)
    security   device tokens
    ingest     applies the events a mirror sends to the tables
    routers/   the HTTP endpoints
    main       creates the FastAPI app
"""
