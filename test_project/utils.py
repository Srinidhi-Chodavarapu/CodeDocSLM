
def validate_email(email):
    """Validate an email address.
    
    @param {string} email - The email address to validate.
    @return {boolean} True if the email is valid, false otherwise.
    """
    if '@' not in email:
        return False
    parts = email.split('@')
    if len(parts) != 2:
        return False
    return '.' in parts[1]


class DataProcessor:
    """DataProcessor class to handle data processing tasks.
    
    This class provides methods to load data from a file, apply filters to the data,
    and process the filtered data.
    
    Attributes:
    - data_source (str): The path to the data file.
    - cache (dict): A cache to store the loaded data for faster access.
    
    Methods:
    - __init__(self, data_source): Initializes the DataProcessor with a data source.
    - process_data(self, filters=None): Processes the data using the provided filters.
    If no filters are provided, all data is processed.
    """
    
    def __init__(self, data_source):
        """Initialize the cache with the given data source.
        
        @param {DataSource} data_source The data source to use for caching.
        """
        self.data_source = data_source
        self.cache = {}
    
    def process_data(self, filters=None):
        """Process data using provided filters.
        
        If no filters are given, all items will be returned.
        
        @param filters: List of filter functions to apply.
        @return: Filtered data.
        """
        if filters is None:
            filters = []
        
        data = self._load_data()
        for filter_func in filters:
            data = [item for item in data if filter_func(item)]
        
        return data
    
    def _load_data(self):
        if 'data' in self.cache:
            return self.cache['data']
        
        with open(self.data_source, 'r') as f:
            data = f.readlines()
        
        self.cache['data'] = data
        return data


def format_currency(amount, currency='USD'):
    """Format an amount in a given currency.
    
    @param {number} amount - The amount to format.
    @param {string} currency - The currency of the amount (default is USD).
    @return {string} The formatted amount.
    """
    symbols = {
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'JPY': '¥'
    }
    
    symbol = symbols.get(currency, '$')
    return f"{symbol}{amount:,.2f}"
