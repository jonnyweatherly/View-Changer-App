"""
Tool implementations for the View Changer App.

These functions are called by the AI chatbot to manipulate view columns.

Run tests locally:
    python -c "from tools_lib import *; print(list_available_columns())"
    python -c "from tools_lib import *; print(list_view_columns())"
    python -c "from tools_lib import *; print(add_column_to_view('firstName', 'First Name', 'varchar', 10, '120px'))"
"""

from models import SessionLocal, PatientColumn, ViewColumn


def list_available_columns(search: str = None):
    """
    List all available patient columns that can be added to a view.
    Optionally filter by search term (matches column_name or label).
    """
    db = SessionLocal()
    try:
        query = db.query(PatientColumn)
        if search:
            search_lower = search.lower()
            query = query.filter(
                (PatientColumn.column_name.ilike(f"%{search_lower}%")) |
                (PatientColumn.label.ilike(f"%{search_lower}%"))
            )
        columns = query.order_by(PatientColumn.label).all()
        return [col.to_dict() for col in columns]
    finally:
        db.close()


def list_view_columns(view_name: str = "vwTitanium_WLAdmin"):
    """
    List all columns currently in the specified view, ordered by grid_order.
    """
    db = SessionLocal()
    try:
        columns = db.query(ViewColumn).filter(
            ViewColumn.view_name == view_name
        ).order_by(ViewColumn.grid_order).all()
        return [col.to_dict() for col in columns]
    finally:
        db.close()


def add_column_to_view(
    column_name: str,
    label: str,
    data_type: str = "varchar",
    grid_order: int = None,
    grid_width: str = "100px",
    is_right_aligned: bool = False,
    view_name: str = "vwTitanium_WLAdmin",
    table_name: str = None
):
    """
    Add a column to the view configuration.
    If grid_order is not specified, adds at the end.
    """
    db = SessionLocal()
    try:
        # Check if column already exists in view
        existing = db.query(ViewColumn).filter(
            ViewColumn.view_name == view_name,
            ViewColumn.column_name == column_name
        ).first()
        
        if existing:
            return {"error": f"Column '{column_name}' already exists in view '{view_name}'"}
        
        # Get max grid_order if not specified
        if grid_order is None:
            max_order = db.query(ViewColumn).filter(
                ViewColumn.view_name == view_name
            ).order_by(ViewColumn.grid_order.desc()).first()
            grid_order = (max_order.grid_order + 1) if max_order else 1
        
        # Create new view column
        view_col = ViewColumn(
            view_name=view_name,
            table_name=table_name,
            column_name=column_name,
            data_type=data_type,
            label=label,
            grid_order=grid_order,
            grid_width=grid_width,
            is_right_aligned=is_right_aligned
        )
        db.add(view_col)
        db.commit()
        db.refresh(view_col)
        
        return {
            "success": True,
            "message": f"Added column '{label}' to view at position {grid_order}",
            "column": view_col.to_dict()
        }
    finally:
        db.close()


def remove_column_from_view(column_name: str, view_name: str = "vwTitanium_WLAdmin"):
    """
    Remove a column from the view configuration.
    """
    db = SessionLocal()
    try:
        column = db.query(ViewColumn).filter(
            ViewColumn.view_name == view_name,
            ViewColumn.column_name == column_name
        ).first()
        
        if not column:
            return {"error": f"Column '{column_name}' not found in view '{view_name}'"}
        
        label = column.label
        db.delete(column)
        db.commit()
        
        return {
            "success": True,
            "message": f"Removed column '{label}' from view"
        }
    finally:
        db.close()


def update_column_order(column_name: str, new_order: int, view_name: str = "vwTitanium_WLAdmin"):
    """
    Update the grid order of a column in the view.
    """
    db = SessionLocal()
    try:
        column = db.query(ViewColumn).filter(
            ViewColumn.view_name == view_name,
            ViewColumn.column_name == column_name
        ).first()
        
        if not column:
            return {"error": f"Column '{column_name}' not found in view '{view_name}'"}
        
        column.grid_order = new_order
        db.commit()
        
        return {
            "success": True,
            "message": f"Updated '{column.label}' to position {new_order}"
        }
    finally:
        db.close()


def update_column_width(column_name: str, new_width: str, view_name: str = "vwTitanium_WLAdmin"):
    """
    Update the width of a column in the view.
    """
    db = SessionLocal()
    try:
        column = db.query(ViewColumn).filter(
            ViewColumn.view_name == view_name,
            ViewColumn.column_name == column_name
        ).first()
        
        if not column:
            return {"error": f"Column '{column_name}' not found in view '{view_name}'"}
        
        column.grid_width = new_width
        db.commit()
        
        return {
            "success": True,
            "message": f"Updated '{column.label}' width to {new_width}"
        }
    finally:
        db.close()


def get_column_info(column_name: str = None, label: str = None):
    """
    Get information about a specific patient column by name or label.
    """
    db = SessionLocal()
    try:
        query = db.query(PatientColumn)
        if column_name:
            query = query.filter(PatientColumn.column_name == column_name)
        elif label:
            query = query.filter(PatientColumn.label.ilike(f"%{label}%"))
        
        columns = query.all()
        return [col.to_dict() for col in columns]
    finally:
        db.close()
