import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from pathlib import Path

from .models import Base

class DBManager:
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Default to data/finance.db in the project root
            root_dir = Path(__file__).resolve().parent.parent
            data_dir = root_dir / "data"
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / "finance.db")
            
        self.db_url = f"sqlite:///{db_path}"
        self.engine = create_engine(self.db_url, connect_args={"check_same_thread": False})
        self.session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(self.session_factory)
        
        # Initialize tables
        self.init_db()

    def init_db(self):
        """Create all tables defined in models if they don't exist."""
        Base.metadata.create_all(self.engine)

    def get_session(self):
        """Provide a transactional scope around a series of operations."""
        return self.Session()

    def close(self):
        self.Session.remove()

# Singleton instance for the application to use
db = DBManager()
