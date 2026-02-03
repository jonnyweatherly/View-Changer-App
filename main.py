"""
View Changer App - FastAPI Backend

Main application file with:
- Static file serving for frontend
- CRUD API endpoints for patient_columns and view_columns
- AI chat endpoint with streaming and tool use

Run locally:
    uvicorn main:app --reload --port 8000
    
Then open http://localhost:8000 in a browser.
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import anthropic
import json
import os
from dotenv import load_dotenv

import tools_lib
import tools_lib
from models import SessionLocal, PatientColumn, ViewColumn, Patient
import random
from datetime import datetime, timedelta


load_dotenv()

def seed_patients():
    """Seed the database with dummy patients if empty."""
    db = SessionLocal()
    try:
        if db.query(Patient).count() == 0:
            print("Seeding dummy patients...")
            names = ["Jonny", "Lynne", "Paul", "Chris", "Elizabeth", "Andrew"]
            last_names = ["Smith", "Jones", "Wilson", "Brown", "Taylor", "Evans"]
            
            for i, name in enumerate(names):
                # Random DOB between 1950 and 2000
                start_date = datetime(1950, 1, 1)
                end_date = datetime(2000, 1, 1)
                random_days = random.randrange((end_date - start_date).days)
                dob = start_date + timedelta(days=random_days)
                
                p = Patient(
                    firstName=name,
                    lastName=last_names[i],
                    dtBirth=dob.strftime("%Y-%m-%d"),
                    Waitlist="General",
                    Priority=random.choice(["Routine", "Urgent"]),
                    Status="Active",
                    DaysWaiting=random.randint(5, 500)
                )
                db.add(p)
            db.commit()
    finally:
        db.close()

seed_patients()

app = FastAPI(title="View Changer App")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files
app.mount("/Application", StaticFiles(directory="Application"), name="app")
app.mount("/html_pages", StaticFiles(directory="html_pages"), name="html")


# --- Tool Definitions ---
TOOL_DEFINITIONS = [
    {
        "name": "list_available_columns",
        "description": "List all available patient columns that can be added to the view. These are columns from the patient database that are not yet in the current view. Use this to show the user what columns they can add.",
        "input_schema": {
            "type": "object",
            "properties": {
                "search": {
                    "type": "string",
                    "description": "Optional search term to filter columns by name or label"
                }
            },
            "required": []
        }
    },
    {
        "name": "list_view_columns",
        "description": "List all columns currently configured in the view. Shows the current state of the view including column order, width, and display properties.",
        "input_schema": {
            "type": "object",
            "properties": {
                "view_name": {
                    "type": "string",
                    "description": "Name of the view (default: vwTitanium_WLAdmin)"
                }
            },
            "required": []
        }
    },
    {
        "name": "add_column_to_view",
        "description": "Add a new column to the view configuration. The column will appear in the view table with the specified properties.",
        "input_schema": {
            "type": "object",
            "properties": {
                "column_name": {
                    "type": "string",
                    "description": "Technical name of the column (e.g., 'firstName', 'dateOfBirth')"
                },
                "label": {
                    "type": "string",
                    "description": "Display label for the column header (e.g., 'First Name', 'Date of Birth')"
                },
                "data_type": {
                    "type": "string",
                    "description": "Data type of the column (varchar, int, datetime, bit, etc.)"
                },
                "grid_order": {
                    "type": "integer",
                    "description": "Position of the column in the view (optional, defaults to end)"
                },
                "grid_width": {
                    "type": "string",
                    "description": "Width of the column (e.g., '100px', '150px')"
                },
                "is_right_aligned": {
                    "type": "boolean",
                    "description": "Whether the column content should be right-aligned"
                }
            },
            "required": ["column_name", "label"]
        }
    },
    {
        "name": "remove_column_from_view",
        "description": "Remove a column from the view configuration. The column will no longer appear in the view table.",
        "input_schema": {
            "type": "object",
            "properties": {
                "column_name": {
                    "type": "string",
                    "description": "Technical name of the column to remove"
                },
                "view_name": {
                    "type": "string",
                    "description": "Name of the view (default: vwTitanium_WLAdmin)"
                }
            },
            "required": ["column_name"]
        }
    },
    {
        "name": "update_column_order",
        "description": "Change the position/order of a column in the view.",
        "input_schema": {
            "type": "object",
            "properties": {
                "column_name": {
                    "type": "string",
                    "description": "Technical name of the column to reorder"
                },
                "new_order": {
                    "type": "integer",
                    "description": "New position for the column"
                },
                "view_name": {
                    "type": "string",
                    "description": "Name of the view (default: vwTitanium_WLAdmin)"
                }
            },
            "required": ["column_name", "new_order"]
        }
    },
    {
        "name": "update_column_width",
        "description": "Change the display width of a column in the view.",
        "input_schema": {
            "type": "object",
            "properties": {
                "column_name": {
                    "type": "string",
                    "description": "Technical name of the column"
                },
                "new_width": {
                    "type": "string",
                    "description": "New width for the column (e.g., '120px', '200px')"
                },
                "view_name": {
                    "type": "string",
                    "description": "Name of the view (default: vwTitanium_WLAdmin)"
                }
            },
            "required": ["column_name", "new_width"]
        }
    },
    {
        "name": "get_column_info",
        "description": "Get detailed information about a specific patient column by its name or label.",
        "input_schema": {
            "type": "object",
            "properties": {
                "column_name": {
                    "type": "string",
                    "description": "Technical name of the column"
                },
                "label": {
                    "type": "string",
                    "description": "Display label to search for"
                }
            },
            "required": []
        }
    }
]


def build_system_prompt():
    """Build the system prompt for the AI assistant."""
    return """You are a helpful assistant for managing database view configurations. 

Your job is to help users customize which columns appear in their data view by:
- Adding new columns from the available patient columns
- Removing columns they don't need
- Reordering columns to their preference
- Adjusting column widths

When the user asks to see available columns, show them in a clear, organized way.
When they want to add a column, find the matching column from the patient columns list and add it.
When they want to remove a column, remove it from the view.

Always confirm what actions you've taken and offer to make additional changes.

Be conversational and helpful. If the user's request is unclear, ask for clarification.
When showing column lists, format them nicely with the label (display name) and column_name (technical name).
"""


def execute_tool(tool_name: str, tool_input: dict):
    """Execute a tool and return its result."""
    tool_map = {
        "list_available_columns": lambda: tools_lib.list_available_columns(**tool_input),
        "list_view_columns": lambda: tools_lib.list_view_columns(**tool_input),
        "add_column_to_view": lambda: tools_lib.add_column_to_view(**tool_input),
        "remove_column_from_view": lambda: tools_lib.remove_column_from_view(**tool_input),
        "update_column_order": lambda: tools_lib.update_column_order(**tool_input),
        "update_column_width": lambda: tools_lib.update_column_width(**tool_input),
        "get_column_info": lambda: tools_lib.get_column_info(**tool_input),
    }
    
    try:
        if tool_name not in tool_map:
            return {"error": f"Unknown tool: {tool_name}"}
        return {"success": True, "data": tool_map[tool_name]()}
    except Exception as e:
        return {"error": str(e)}


# --- Routes ---

@app.get("/")
def root():
    """Serve the main HTML page."""
    return FileResponse("html_pages/index.html")


@app.get("/api/patient-columns")
def get_patient_columns(search: str = None):
    """List all available patient columns."""
    columns = tools_lib.list_available_columns(search)
    return {"columns": columns}


@app.get("/api/view-columns")
def get_view_columns(view_name: str = "vwTitanium_WLAdmin"):
    """List columns in the current view."""
    columns = tools_lib.list_view_columns(view_name)
    return {"columns": columns}


@app.get("/api/patients")
def get_patients(view_name: str = "vwTitanium_WLAdmin"):
    """Get patient data formatted for the view."""
    db = SessionLocal()
    try:
        patients = db.query(Patient).all()
        view_cols_config = tools_lib.list_view_columns(view_name)
        view_col_names = [c['column_name'] for c in view_cols_config]
        
        results = []
        for i, p in enumerate(patients):
            # Base dict
            p_dict = p.to_dict()
            
            # Add computed/aliased fields that the View expects
            p_dict["PatientName"] = f"{p.firstName} {p.lastName}"
            p_dict["RowNumber"] = i + 1
            p_dict["Patient Primary Id"] = p.id
            
            # PatientAge
            if p.dtBirth:
                try:
                    dob = datetime.strptime(p.dtBirth, "%Y-%m-%d")
                    p_dict["PatientAge"] = datetime.now().year - dob.year
                except:
                    p_dict["PatientAge"] = 0
            else:
                p_dict["PatientAge"] = 0
            
            # Ensure all view columns exist in the dict (with default values if missing)
            for col_name in view_col_names:
                if col_name not in p_dict:
                    # Provide reasonable defaults based on likely type
                    p_dict[col_name] = None
                    
                    if col_name == "ProviderName":
                         p_dict[col_name] = "Dr. Smith"
                    elif col_name == "Listed":
                        p_dict[col_name] = "2024-01-15"
                    elif col_name == "Assigned":
                        p_dict[col_name] = "2024-02-01"
            
            results.append(p_dict)
            
        return {"data": results}
    finally:
        db.close()


@app.post("/api/view-columns")
async def add_view_column(request: Request):
    """Add a column to the view."""
    data = await request.json()
    result = tools_lib.add_column_to_view(**data)
    return result


@app.delete("/api/view-columns/{column_name}")
def delete_view_column(column_name: str, view_name: str = "vwTitanium_WLAdmin"):
    """Remove a column from the view."""
    result = tools_lib.remove_column_from_view(column_name, view_name)
    return result


@app.post("/api/chat")
async def chat(request: Request):
    """AI chat endpoint with streaming and tool use."""
    
    # Check for API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or api_key == "your-key-here":
        return JSONResponse(
            status_code=500,
            content={"error": "ANTHROPIC_API_KEY not configured. Please add your API key to .env file."}
        )
    
    data = await request.json()
    messages = data.get("messages", [])
    
    client = anthropic.Anthropic(api_key=api_key)
    system_prompt = build_system_prompt()
    
    def stream():
        try:
            response = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4096,
                system=system_prompt,
                messages=messages,
                tools=TOOL_DEFINITIONS
            )
            
            # Tool execution loop
            while response.stop_reason == "tool_use":
                tool_results = []
                
                for block in response.content:
                    if block.type == "tool_use":
                        result = execute_tool(block.name, block.input)
                        yield json.dumps({
                            "type": "tool_result",
                            "name": block.name,
                            "result": result
                        }) + "\n"
                        
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result)
                        })
                
                # Continue conversation with tool results
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
                
                response = client.messages.create(
                    model="claude-sonnet-4-5",
                    max_tokens=4096,
                    system=system_prompt,
                    messages=messages,
                    tools=TOOL_DEFINITIONS
                )
            
            # Final text response
            text = "".join(
                block.text for block in response.content if hasattr(block, "text")
            )
            yield json.dumps({"type": "reply", "content": text}) + "\n"
            yield json.dumps({"type": "done"}) + "\n"
            
        except anthropic.AuthenticationError:
            yield json.dumps({"type": "error", "content": "Invalid API key. Please check your ANTHROPIC_API_KEY in .env"}) + "\n"
        except Exception as e:
            yield json.dumps({"type": "error", "content": str(e)}) + "\n"
    
    return StreamingResponse(stream(), media_type="application/x-ndjson")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
