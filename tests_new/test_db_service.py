import pytest
from unittest.mock import patch, MagicMock
from app.agents.database.db_service import (
    generate_sql_from_llm,
    execute_sql_query,
    fetch_order_details,
    check_existing_request,
    fetch_orders_by_email,
    record_approved_request,
    cancel_existing_request,
    get_user_by_email,
    create_user,
    save_chat_message,
    get_chat_history_by_email,
)
from app.agents.database.schemas.db_models import Orders, CustomerRequests, Users, ChatHistory

@patch("app.agents.database.db_service.get_db_session")
def test_execute_sql_query(mock_get_db_session):
    mock_db = MagicMock()
    mock_get_db_session.return_value = mock_db
    mock_result = MagicMock()
    mock_db.execute.return_value = mock_result
    mock_result.fetchone.return_value = {"order_id": 123}
    
    assert execute_sql_query("SELECT * FROM orders;") == {"order_id": 123}
    mock_db.close.assert_called_once()
    
    mock_db.execute.side_effect = Exception("DB error")
    with pytest.raises(Exception):
        execute_sql_query("SELECT * FROM orders;")

@patch("app.agents.database.db_service.ollama", create=True)
@patch("app.agents.database.db_service.OLLAMA_AVAILABLE", True)
def test_generate_sql_from_llm_with_ollama(mock_ollama):
    mock_ollama.chat.return_value = {
        "message": {"content": "```sql\nSELECT * FROM orders WHERE order_id = 123 AND user_email = 'test@example.com';\n```"}
    }
    sql = generate_sql_from_llm(123, "test@example.com")
    assert "SELECT * FROM orders" in sql
    assert sql.endswith(";")

@patch("app.agents.database.db_service.OLLAMA_AVAILABLE", False)
def test_generate_sql_from_llm_without_ollama():
    sql = generate_sql_from_llm(123, "test@example.com")
    assert sql == "SELECT * FROM orders WHERE order_id = 123 AND user_email = 'test@example.com';"

@patch("app.agents.database.db_service.generate_sql_from_llm")
@patch("app.agents.database.db_service.execute_sql_query")
def test_fetch_order_details(mock_execute, mock_generate):
    mock_generate.return_value = "SELECT * FROM orders;"
    
    mock_row = MagicMock()
    mock_row.order_id = 123
    mock_row.user_id = "user1"
    mock_row.product = "Laptop"
    mock_row.description = "A laptop"
    mock_row.quantity = 1
    mock_row.order_date = "2023-01-01"
    mock_row.delivered_date = "2023-01-05"
    mock_row.status = "Delivered"
    mock_row.amount = 1000
    
    mock_execute.return_value = mock_row
    
    result = fetch_order_details(123)
    assert result["order_found"] is True
    assert result["order_details"]["order_id"] == 123
    
    mock_execute.return_value = None
    result = fetch_order_details(123)
    assert result["order_found"] is False
    assert "not found" in result["error"]

def test_fetch_order_details_invalid():
    result = fetch_order_details("not_an_int")
    assert result["order_found"] is False
    assert "Invalid order_id format" in result["error"]

@patch("app.agents.database.db_service.execute_sql_query", side_effect=Exception("Database error"))
@patch("app.agents.database.db_service.generate_sql_from_llm")
def test_fetch_order_details_exception(mock_gen, mock_exec):
    mock_gen.return_value = "SELECT * FROM orders"
    result = fetch_order_details(123)
    assert result["order_found"] is False
    assert "Database error" in result["error"]

@patch("app.agents.database.db_service.get_db_session")
def test_check_existing_request(mock_get_db_session):
    mock_db = MagicMock()
    mock_get_db_session.return_value = mock_db
    mock_query = MagicMock()
    mock_db.query.return_value = mock_query
    mock_filter = MagicMock()
    mock_query.filter.return_value = mock_filter
    mock_filter.first.return_value = MagicMock(order_id=123)
    
    result = check_existing_request(123)
    assert result.order_id == 123
    mock_db.close.assert_called_once()

@patch("app.agents.database.db_service.get_db_session")
def test_fetch_orders_by_email(mock_get_db_session):
    mock_db = MagicMock()
    mock_get_db_session.return_value = mock_db
    mock_db.query().filter().all.return_value = [MagicMock(order_id=1)]
    result = fetch_orders_by_email("test@test.com")
    assert len(result) == 1

@patch("app.agents.database.db_service.get_db_session")
def test_record_approved_request(mock_get_db_session):
    mock_db = MagicMock()
    mock_get_db_session.return_value = mock_db
    
    # Success
    result = record_approved_request(123, "test@test.com", "refund")
    assert result is True
    mock_db.commit.assert_called_once()
    mock_db.close.assert_called_once()
    
    # Exception
    mock_db.commit.side_effect = Exception("error")
    result = record_approved_request(123, "test@test.com", "refund")
    assert result is False
    mock_db.rollback.assert_called_once()

@patch("app.agents.database.db_service.get_db_session")
def test_cancel_existing_request(mock_get_db_session):
    mock_db = MagicMock()
    mock_get_db_session.return_value = mock_db
    mock_req = MagicMock()
    mock_db.query().filter().first.side_effect = [mock_req, MagicMock()]
    
    result = cancel_existing_request(123)
    assert result is True
    assert mock_req.status == "canceled"
    mock_db.commit.assert_called_once()
    
    # Not found
    mock_db.query().filter().first.side_effect = [None]
    result = cancel_existing_request(123)
    assert result is False
    
    # Exception
    mock_db.query().filter().first.side_effect = Exception("error")
    result = cancel_existing_request(123)
    assert result is False
    mock_db.rollback.assert_called_once()

@patch("app.agents.database.db_service.get_db_session")
def test_get_user_by_email(mock_get_db_session):
    mock_db = MagicMock()
    mock_get_db_session.return_value = mock_db
    mock_db.query().filter().first.return_value = MagicMock(email="test@test.com")
    
    result = get_user_by_email("test@test.com")
    assert result.email == "test@test.com"

@patch("app.agents.database.db_service.get_db_session")
def test_create_user(mock_get_db_session):
    mock_db = MagicMock()
    mock_get_db_session.return_value = mock_db
    
    result = create_user("test@test.com", "hash")
    assert result is not None
    mock_db.commit.assert_called_once()
    
    # Exception
    mock_db.commit.side_effect = Exception("error")
    result = create_user("test@test.com", "hash")
    assert result is None

@patch("app.agents.database.db_service.get_db_session")
def test_save_chat_message(mock_get_db_session):
    mock_db = MagicMock()
    mock_get_db_session.return_value = mock_db
    save_chat_message("user@test.com", "user", "hi", "conv1")
    mock_db.commit.assert_called_once()
    
    mock_db.commit.side_effect = Exception("error")
    save_chat_message("user@test.com", "user", "hi", "conv1")
    mock_db.rollback.assert_called_once()

@patch("app.agents.database.db_service.get_db_session")
def test_get_chat_history_by_email(mock_get_db_session):
    mock_db = MagicMock()
    mock_get_db_session.return_value = mock_db
    mock_hist = MagicMock()
    mock_hist.role = "user"
    mock_hist.content = "hi"
    mock_hist.conversation_id = "conv1"
    mock_db.query().filter().order_by().all.return_value = [mock_hist]
    
    result = get_chat_history_by_email("user@test.com")
    assert len(result) == 1
    assert result[0]["content"] == "hi"

