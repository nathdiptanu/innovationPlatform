def build_openapi():
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "GRIT Competition API",
            "version": "1.0.0",
            "description": "Public idea submission and protected management endpoints for Grassroot Innovation In Technology.",
        },
        "servers": [{"url": "/"}],
        "paths": {
            "/api/cycles/current": {
                "get": {
                    "summary": "Get the current non-archived cycle",
                    "responses": {"200": {"description": "Cycle", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Cycle"}}}}},
                }
            },
            "/api/categories": {
                "get": {
                    "summary": "List categories for the current cycle",
                    "responses": {"200": {"description": "Category list", "content": {"application/json": {"schema": {"type": "array", "items": {"$ref": "#/components/schemas/Category"}}}}}},
                }
            },
            "/api/ideas": {
                "get": {
                    "summary": "Search ideas by idea ID, problem statement, or employee ID",
                    "parameters": [
                        {"name": "q", "in": "query", "schema": {"type": "string"}},
                        {"name": "page", "in": "query", "schema": {"type": "integer", "minimum": 1}},
                    ],
                    "responses": {"200": {"description": "Paged ideas", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/IdeaPage"}}}}},
                },
                "post": {
                    "summary": "Submit an idea while the cycle is open",
                    "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/IdeaInput"}}}},
                    "responses": {
                        "201": {"description": "Idea created", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/IdeaReceipt"}}}},
                        "400": {"description": "Validation error"},
                        "409": {"description": "Submission window closed"},
                    },
                },
            },
            "/api/ideas/{idea_id}": {
                "get": {
                    "summary": "Get an idea",
                    "parameters": [{"$ref": "#/components/parameters/IdeaId"}],
                    "responses": {"200": {"description": "Idea", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Idea"}}}}},
                },
                "put": {
                    "summary": "Edit an idea while the cycle is open",
                    "parameters": [{"$ref": "#/components/parameters/IdeaId"}, {"$ref": "#/components/parameters/EditToken"}],
                    "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/IdeaInput"}}}},
                    "responses": {"200": {"description": "Updated idea"}, "403": {"description": "Missing edit token"}, "409": {"description": "Cycle closed"}},
                },
            },
            "/api/core/dashboard": {
                "get": {
                    "summary": "Core committee idea counts by category",
                    "responses": {"200": {"description": "Dashboard counts"}, "403": {"description": "Core access required"}},
                }
            },
        },
        "components": {
            "parameters": {
                "IdeaId": {"name": "idea_id", "in": "path", "required": True, "schema": {"type": "string"}},
                "EditToken": {"name": "X-Edit-Token", "in": "header", "required": True, "schema": {"type": "string"}},
            },
            "schemas": {
                "Cycle": {"type": "object", "properties": {"id": {"type": "string"}, "name": {"type": "string"}, "start_at": {"type": "string", "format": "date-time"}, "end_at": {"type": "string", "format": "date-time"}, "submission_open": {"type": "boolean"}}},
                "Category": {"type": "object", "properties": {"id": {"type": "string"}, "name": {"type": "string"}, "top_ideas_required": {"type": "integer"}}},
                "Contributor": {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}, "username": {"type": "string"}}},
                "IdeaInput": {
                    "type": "object",
                    "required": ["problem_statement", "solution_summary", "production_readiness", "contributors", "officer_sponsor", "content", "category_ids", "owner_name", "owner_employee_id", "office_location", "india_region"],
                    "properties": {
                        "problem_statement": {"type": "string"},
                        "solution_summary": {"type": "string"},
                        "video_link": {"type": "string", "format": "uri"},
                        "can_be_patented": {"type": "boolean"},
                        "is_patented": {"type": "boolean"},
                        "production_readiness": {"type": "string", "enum": ["yes", "no", "in_6_months"]},
                        "contributors": {"type": "array", "minItems": 1, "maxItems": 5, "items": {"$ref": "#/components/schemas/Contributor"}},
                        "team_name": {"type": "string"},
                        "officer_sponsor": {"type": "string"},
                        "content_format": {"type": "string", "enum": ["plain", "html"]},
                        "content": {"type": "string"},
                        "category_ids": {"type": "array", "minItems": 1, "maxItems": 2, "items": {"type": "string"}},
                        "owner_name": {"type": "string"},
                        "owner_employee_id": {"type": "string"},
                        "office_location": {"type": "string"},
                        "india_region": {"type": "string"},
                    },
                },
                "Idea": {"allOf": [{"$ref": "#/components/schemas/IdeaInput"}, {"type": "object", "properties": {"idea_id": {"type": "string"}, "created_at": {"type": "string", "format": "date-time"}, "updated_at": {"type": "string", "format": "date-time"}}}]},
                "IdeaReceipt": {"type": "object", "properties": {"idea_id": {"type": "string"}, "edit_token": {"type": "string"}, "edit_url": {"type": "string"}}},
                "IdeaPage": {"type": "object", "properties": {"items": {"type": "array", "items": {"$ref": "#/components/schemas/Idea"}}, "page": {"type": "integer"}, "total": {"type": "integer"}}},
            },
        },
    }
