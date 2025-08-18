import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from app.db import get_db
from app.core.store import get_session, save_session
from app.core.esg_analysis import agent_executors

def test_session_flow():
    # Get database session
    db = next(get_db())
    
    # Test session data
    test_session_id = "test_session_123"
    test_data = {
        "messages": ["test1", "test2"],
        "agent_executor": True,
        "company_name": "Test Company"
    }
    
    # Save session
    print(f"Saving test session {test_session_id}...")
    save_success = save_session(test_session_id, test_data, db)
    print(f"Save result: {save_success}")
    
    # Retrieve session
    print(f"\nRetrieving test session {test_session_id}...")
    retrieved_data = get_session(test_session_id, db)
    print(f"Retrieved data: {retrieved_data}")
    
    # Test agent_executors reconstruction
    print("\nTesting agent_executors reconstruction...")
    if test_session_id in agent_executors:
        print(f"Agent already exists for {test_session_id}")
    else:
        print(f"Agent not found, testing reconstruction...")
        from app.core.esg_analysis import create_esg_agent
        agent = create_esg_agent(test_session_id, None, "Test Company")
        agent_executors[test_session_id] = agent
        print(f"Agent created and registered for {test_session_id}")
    
    # Cleanup
    db.close()

def test_real_session():
    """Test the actual session s_3bb4a43950934a62"""
    db = next(get_db())
    session_id = "s_3bb4a43950934a62"
    
    print(f"\nTesting real session {session_id}...")
    session_data = get_session(session_id, db)
    if session_data:
        print(f"Session found with data: {session_data.keys()}")
    else:
        print(f"Session {session_id} not found")
    
    db.close()

if __name__ == "__main__":
    test_session_flow()
    test_real_session()
