import os
import pandas as pd
import logging
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
import pyodbc
import psycopg2
from mysql import connector
try:
    import cx_Oracle
except ImportError:
    cx_Oracle = None

logger = logging.getLogger(__name__)

class DatabaseConnector:
    """
    A class to handle connections to various database types and provide
    standardized methods for querying and updating data.
    """
    def __init__(self, db_type, host, port, database, username, password, **kwargs):
        """Initialize the database connector with connection parameters."""
        self.db_type = db_type.lower()
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.kwargs = kwargs
        self.engine = None
        self.connection_string = None
        self._create_connection_string()

    def _create_connection_string(self):
        """Create the appropriate connection string based on database type."""
        if self.db_type == 'mysql':
            self.connection_string = f"mysql+mysqlconnector://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        elif self.db_type == 'postgresql':
            self.connection_string = f"postgresql+psycopg2://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        elif self.db_type == 'sqlserver':
            self.connection_string = f"mssql+pyodbc://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}?driver=ODBC+Driver+17+for+SQL+Server"
        elif self.db_type == 'oracle':
            if not cx_Oracle:
                raise ImportError("cx_Oracle package is required for Oracle connections")
            # Oracle connection string format: oracle+cx_oracle://user:pass@host:port/?service_name=service
            service_name = self.kwargs.get('service_name', self.database)
            self.connection_string = f"oracle+cx_oracle://{self.username}:{self.password}@{self.host}:{self.port}/?service_name={service_name}"
        elif self.db_type == 'sqlite':
            # SQLite connection string format: sqlite:///path/to/database.db
            db_path = self.kwargs.get('db_path', self.database)
            self.connection_string = f"sqlite:///{db_path}"
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")

    def connect(self):
        """Establish a connection to the database."""
        try:
            connect_args = {}
            if self.db_type == 'oracle':
                connect_args['encoding'] = 'UTF-8'
                connect_args['nencoding'] = 'UTF-8'
            elif self.db_type == 'sqlite':
                connect_args['check_same_thread'] = False

            self.engine = create_engine(
                self.connection_string,
                echo=False,
                pool_pre_ping=True,
                connect_args=connect_args
            )

            # Test the connection
            with self.engine.connect() as conn:
                pass
            logger.info(f"Successfully connected to {self.db_type} database: {self.database}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Database connection error: {str(e)}")
            return False

    def disconnect(self):
        """Close the database connection."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connection closed")

    def get_tables(self):
        """Get a list of tables in the database."""
        try:
            with self.engine.connect() as conn:
                inspector = inspect(self.engine)
                tables = inspector.get_table_names()
                return tables
        except SQLAlchemyError as e:
            logger.error(f"Error getting tables: {str(e)}")
            return []

    def get_columns(self, table_name):
        """Get column information for a specific table."""
        try:
            with self.engine.connect() as conn:
                inspector = inspect(self.engine)
                columns = inspector.get_columns(table_name)

                # Process columns to make them JSON serializable
                processed_columns = []
                for col in columns:
                    # Convert SQLAlchemy type objects to strings
                    col_type = str(col['type']).split('(')[0] if '(' in str(col['type']) else str(col['type'])
                    processed_columns.append({
                        'name': col['name'],
                        'type': col_type,
                        'nullable': col.get('nullable', True),
                        'primary_key': col.get('primary_key', False),
                        'default': str(col.get('default', None))
                    })
                return processed_columns
        except SQLAlchemyError as e:
            logger.error(f"Error getting columns for table {table_name}: {str(e)}")
            return []

    def execute_query(self, query, params=None):
        """Execute a SQL query and return the results as a pandas DataFrame."""
        try:
            with self.engine.connect() as conn:
                if params:
                    result = conn.execute(text(query), params)
                else:
                    result = conn.execute(text(query))

                if result.returns_rows:
                    df = pd.DataFrame(result.fetchall())
                    if not df.empty:
                        df.columns = result.keys()
                    return df
                return pd.DataFrame()
        except SQLAlchemyError as e:
            logger.error(f"Query execution error: {str(e)}")
            return pd.DataFrame()

    def update_data(self, table_name, data_df, primary_key):
        """Update data in the database table from a pandas DataFrame."""
        try:
            # Use pandas to_sql method with 'replace' if table exists
            data_df.to_sql(name=table_name, con=self.engine, if_exists='replace', index=False)
            logger.info(f"Data updated successfully in table: {table_name}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error updating data in table {table_name}: {str(e)}")
            return False

    def get_primary_keys(self, table_name):
        """Get primary key columns for a specific table."""
        try:
            with self.engine.connect() as conn:
                inspector = inspect(self.engine)
                pk_constraint = inspector.get_pk_constraint(table_name)
                return pk_constraint.get('constrained_columns', [])
        except SQLAlchemyError as e:
            logger.error(f"Error getting primary keys for table {table_name}: {str(e)}")
            return []

    def get_foreign_keys(self, table_name):
        """Get foreign key relationships for a specific table."""
        try:
            with self.engine.connect() as conn:
                inspector = inspect(self.engine)
                foreign_keys = inspector.get_foreign_keys(table_name)
                return foreign_keys
        except SQLAlchemyError as e:
            logger.error(f"Error getting foreign keys for table {table_name}: {str(e)}")
            return []

    @staticmethod
    def get_db_connection_from_model(db_conn_model):
        """Create a DatabaseConnector instance from a DBConnection model."""
        extra_params = {}
        if db_conn_model.db_type == 'oracle':
            extra_params['service_name'] = db_conn_model.database
        elif db_conn_model.db_type == 'sqlite':
            extra_params['db_path'] = db_conn_model.database

        return DatabaseConnector(
            db_type=db_conn_model.db_type,
            host=db_conn_model.host, 
            port=db_conn_model.port,
            database=db_conn_model.database,
            username=db_conn_model.username,
            password=db_conn_model.password,
            **extra_params
        )

    def test_connection(self):
        """Test the database connection and return basic information."""
        try:
            if self.connect():
                tables = self.get_tables()
                table_count = len(tables)
                sample_tables = tables[:5] if table_count > 5 else tables
                return {
                    'success': True,
                    'message': f'Successfully connected to {self.db_type} database',
                    'database_name': self.database,
                    'table_count': table_count,
                    'sample_tables': sample_tables
                }
            return {
                'success': False,
                'message': 'Failed to connect to database'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error testing connection: {str(e)}'
            }
        finally:
            self.disconnect()