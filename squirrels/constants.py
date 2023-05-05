# Squirrels CLI commands
INIT_CMD = 'init'
LOAD_MODULES_CMD = 'load-modules'
GET_CREDS_CMD = 'get-all-credentials'
SET_CRED_CMD = 'set-credential'
DELETE_CRED_CMD = 'delete-credential'
TEST_CMD = 'test'
RUN_CMD = 'run'

# Manifest file keys
DB_CONNECTION_KEY = 'db_connection'
MODULES_KEY = 'modules'
DATASET_LABEL_KEY = 'label'
DATASETS_KEY = 'datasets'
HEADERS_KEY = 'headers'
DATABASE_VIEWS_KEY = 'database_views'
DB_VIEW_NAME_KEY = 'name'
DB_VIEW_FILE_KEY = 'file'
FINAL_VIEW_KEY = 'final_view'
BASE_PATH_KEY = 'base_path'
SETTINGS_KEY = 'settings'

# Database credentials keys
CREDENTIALS_KEY = 'credentials'
USERNAME_KEY = 'username'
PASSWORD_KEY = 'password'

# Folder/File names
MANIFEST_FILE = 'squirrels.yaml'
PROJ_VARS_FILE = 'project_vars.yaml'
CONNECTIONS_FILE = 'connections.py'
OUTPUTS_FOLDER = 'outputs'
MODULES_FOLDER = 'modules'
DATASETS_FOLDER = 'datasets'
PARAMETERS_FILE = 'parameters.py'
PARAMETERS_OUTPUT = 'parameters.json'
DATABASE_VIEW_SQL_FILE = 'database_view1.sql.j2'
DATABASE_VIEW_PY_FILE = 'database_view1.py'
FINAL_VIEW_SQL_NAME = 'final_view.sql.j2'
FINAL_VIEW_PY_NAME = 'final_view.py'
FINAL_VIEW_OUT_STEM = 'final_view'
CONTEXT_FILE = 'context.py'
SELECTIONS_CFG_FILE = 'selections.cfg'

# Dataset setting names
PARAMETERS_CACHE_SIZE_SETTING = 'parameters.cache.size'
PARAMETERS_CACHE_TTL_SETTING = 'parameters.cache.ttl'
RESULTS_CACHE_SIZE_SETTING = 'results.cache.size'
RESULTS_CACHE_TTL_SETTING = 'results.cache.ttl'

# Selection cfg sections
PARAMETERS_SECTION = 'parameters'
HEADERS_SECTION = 'headers'
