import re
import random
import datetime
import uuid
import hashlib
import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class RuleEngine:
    """
    Engine that applies de-identification rules to data.
    Contains all the logic for different types of transformations.
    """
    def __init__(self):
        self.rules = []
        self.transformers = {
            'patient_id': self._transform_patient_id,
            'date_offset': self._transform_date_offset,
            'date_generalization': self._transform_date_generalization,
            'phone_mask': self._transform_phone,
            'email_mask': self._transform_email,
            'text_redaction': self._transform_text_redaction,
            'fixed_value': self._transform_fixed_value,
            'hash': self._transform_hash,
            'random_value': self._transform_random_value,
            'zipcode_truncate': self._transform_zipcode
        }
    
    def load_rules(self, rules):
        """Load rules into the rule engine."""
        self.rules = rules
        logger.info(f"Loaded {len(rules)} rules into the rule engine")
    
    def column_matches_rule(self, table_name, column_name, rule):
        """Check if a column matches a specific rule based on rule configuration."""
        config = rule.get_config()
        
        # Check if the rule has table and column patterns
        if 'tables' in config and 'columns' in config:
            table_patterns = config['tables']
            column_patterns = config['columns']
            
            # Check if any table pattern matches
            table_match = False
            for pattern in table_patterns:
                if re.match(pattern, table_name, re.IGNORECASE):
                    table_match = True
                    break
            
            if not table_match:
                return False
            
            # Check if any column pattern matches
            for pattern in column_patterns:
                if re.match(pattern, column_name, re.IGNORECASE):
                    return True
            
        return False
    
    def apply_rule(self, data_series, rule):
        """Apply a rule to a pandas Series (column) of data."""
        rule_type = rule.rule_type
        config = rule.get_config()
        
        if rule_type in self.transformers:
            # Apply the appropriate transformer function
            return self.transformers[rule_type](data_series, config)
        else:
            logger.warning(f"Unknown rule type: {rule_type}")
            return data_series
    
    def _transform_patient_id(self, data_series, config):
        """Transform patient IDs to de-identified values."""
        prefix = config.get('prefix', 'P')
        format_str = config.get('format', '{}{:07d}')
        
        # Create a mapping for unique values
        unique_values = data_series.unique()
        mapping = {}
        
        for i, val in enumerate(unique_values):
            if pd.notna(val):
                mapping[val] = format_str.format(prefix, i + 1)
        
        # Apply mapping
        return data_series.map(mapping).fillna(data_series)
    
    def _transform_date_offset(self, data_series, config):
        """Offset dates by a random number of days within a range."""
        min_days = config.get('min_days', -30)
        max_days = config.get('max_days', 30)
        seed = config.get('seed', 42)
        
        # Set random seed for reproducibility
        random.seed(seed)
        
        # Function to apply random offset to a date
        def offset_date(date_val):
            if pd.isna(date_val):
                return date_val
            
            try:
                # Convert to datetime if it's a string
                if isinstance(date_val, str):
                    date_val = pd.to_datetime(date_val)
                
                # Apply random offset
                days_offset = random.randint(min_days, max_days)
                return date_val + pd.Timedelta(days=days_offset)
            except:
                return date_val
        
        # Apply the offset to each value
        return data_series.apply(offset_date)
    
    def _transform_date_generalization(self, data_series, config):
        """Generalize dates by keeping only year, month, or setting to first day of month/year."""
        level = config.get('level', 'month')  # year, month, day
        
        # Function to generalize a date
        def generalize_date(date_val):
            if pd.isna(date_val):
                return date_val
            
            try:
                # Convert to datetime if it's a string
                if isinstance(date_val, str):
                    date_val = pd.to_datetime(date_val)
                
                # Apply generalization based on level
                if level == 'year':
                    return datetime.datetime(date_val.year, 1, 1)
                elif level == 'month':
                    return datetime.datetime(date_val.year, date_val.month, 1)
                else:
                    return date_val  # No generalization
            except:
                return date_val
        
        # Apply generalization to each value
        return data_series.apply(generalize_date)
    
    def _transform_phone(self, data_series, config):
        """Mask phone numbers with a pattern."""
        pattern = config.get('pattern', 'XXX-XXX-{last4}')
        
        # Function to mask a phone number
        def mask_phone(phone_val):
            if pd.isna(phone_val):
                return phone_val
            
            try:
                # Remove non-digit characters
                digits = re.sub(r'\D', '', str(phone_val))
                
                # If we have enough digits, apply the mask
                if len(digits) >= 10:
                    last4 = digits[-4:]
                    return pattern.format(last4=last4)
                return phone_val
            except:
                return phone_val
        
        # Apply mask to each value
        return data_series.apply(mask_phone)
    
    def _transform_email(self, data_series, config):
        """Mask email addresses."""
        mode = config.get('mode', 'preserve_domain')  # preserve_domain, full_mask
        
        # Function to mask an email
        def mask_email(email_val):
            if pd.isna(email_val):
                return email_val
            
            try:
                email_str = str(email_val)
                if '@' in email_str:
                    username, domain = email_str.split('@', 1)
                    
                    if mode == 'preserve_domain':
                        masked_username = hashlib.md5(username.encode()).hexdigest()[:8]
                        return f"{masked_username}@{domain}"
                    else:  # full_mask
                        return f"masked_email_{hash(email_str) % 10000:04d}@example.com"
                
                return email_val
            except:
                return email_val
        
        # Apply mask to each value
        return data_series.apply(mask_email)
    
    def _transform_text_redaction(self, data_series, config):
        """Redact or replace sensitive text."""
        patterns = config.get('patterns', [r'\b\d{3}-\d{2}-\d{4}\b'])  # Default: SSN pattern
        replacement = config.get('replacement', '[REDACTED]')
        
        # Function to redact text
        def redact_text(text_val):
            if pd.isna(text_val):
                return text_val
            
            try:
                text_str = str(text_val)
                for pattern in patterns:
                    text_str = re.sub(pattern, replacement, text_str)
                return text_str
            except:
                return text_val
        
        # Apply redaction to each value
        return data_series.apply(redact_text)
    
    def _transform_fixed_value(self, data_series, config):
        """Replace values with a fixed value."""
        value = config.get('value', '[REDACTED]')
        
        # Replace all non-null values with the fixed value
        return data_series.apply(lambda x: value if pd.notna(x) else x)
    
    def _transform_hash(self, data_series, config):
        """Hash values for de-identification."""
        salt = config.get('salt', 'deidentification')
        length = config.get('length', 8)
        
        # Function to hash a value
        def hash_value(val):
            if pd.isna(val):
                return val
            
            try:
                val_str = str(val)
                hashed = hashlib.md5((val_str + salt).encode()).hexdigest()
                return hashed[:length]
            except:
                return val
        
        # Apply hashing to each value
        return data_series.apply(hash_value)
    
    def _transform_random_value(self, data_series, config):
        """Replace values with random values of the same type."""
        seed = config.get('seed', 42)
        random.seed(seed)
        
        # Determine data type
        if data_series.dtype == np.int64 or data_series.dtype == np.int32:
            min_val = config.get('min_val', 0)
            max_val = config.get('max_val', 1000)
            return data_series.apply(lambda x: random.randint(min_val, max_val) if pd.notna(x) else x)
        
        elif data_series.dtype == np.float64 or data_series.dtype == np.float32:
            min_val = config.get('min_val', 0.0)
            max_val = config.get('max_val', 1.0)
            return data_series.apply(lambda x: random.uniform(min_val, max_val) if pd.notna(x) else x)
        
        else:  # Treat as string
            length = config.get('length', 8)
            chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
            return data_series.apply(lambda x: ''.join(random.choice(chars) for _ in range(length)) if pd.notna(x) else x)
    
    def _transform_zipcode(self, data_series, config):
        """Truncate ZIP codes to first 3 digits."""
        # Function to truncate ZIP code
        def truncate_zip(zip_val):
            if pd.isna(zip_val):
                return zip_val
            
            try:
                zip_str = str(zip_val).strip()
                if len(zip_str) >= 5:
                    return zip_str[:3] + "XX"
                return zip_val
            except:
                return zip_val
        
        # Apply truncation to each value
        return data_series.apply(truncate_zip)
