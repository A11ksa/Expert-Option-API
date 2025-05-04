from typing import List
import re
import json

class RawValidator:
    def __init__(self):
        """
        Initialize a RawValidator for low-level validation logic.
        """
        self.pattern = None
        self.check_fn = lambda x: True

    @staticmethod
    def regex(pattern: str):
        """
        Create a validator that checks if a string matches a regex pattern.

        Args:
            pattern (str): Regex pattern to match.

        Returns:
            RawValidator: Validator instance.
        """
        validator = RawValidator()
        validator.pattern = re.compile(pattern)
        validator.check_fn = lambda x: bool(validator.pattern.match(x))
        return validator

    @staticmethod
    def starts_with(prefix: str):
        """
        Create a validator that checks if a string starts with a prefix.

        Args:
            prefix (str): Prefix to check.

        Returns:
            RawValidator: Validator instance.
        """
        validator = RawValidator()
        validator.check_fn = lambda x: x.startswith(prefix)
        return validator

    @staticmethod
    def ends_with(suffix: str):
        """
        Create a validator that checks if a string ends with a suffix.

        Args:
            suffix (str): Suffix to check.

        Returns:
            RawValidator: Validator instance.
        """
        validator = RawValidator()
        validator.check_fn = lambda x: x.endswith(suffix)
        return validator

    @staticmethod
    def contains(substring: str):
        """
        Create a validator that checks if a string contains a substring.

        Args:
            substring (str): Substring to check.

        Returns:
            RawValidator: Validator instance.
        """
        validator = RawValidator()
        validator.check_fn = lambda x: substring in x
        return validator

    @staticmethod
    def json_field(field: str, value: any):
        """
        Create a validator that checks if a JSON message contains a specific field with a value.

        Args:
            field (str): JSON field to check.
            value (any): Expected value of the field.

        Returns:
            RawValidator: Validator instance.
        """
        validator = RawValidator()
        def check_json(x):
            try:
                data = json.loads(x)
                return data.get(field) == value
            except json.JSONDecodeError:
                return False
        validator.check_fn = check_json
        return validator

    @staticmethod
    def ne(validator):
        """
        Create a validator that negates another validator.

        Args:
            validator (RawValidator): Validator to negate.

        Returns:
            RawValidator: Validator instance.
        """
        new_validator = RawValidator()
        new_validator.check_fn = lambda x: not validator.check_fn(x)
        return new_validator

    @staticmethod
    def all(validators):
        """
        Create a validator that requires all validators to pass.

        Args:
            validators (List[RawValidator]): List of validators.

        Returns:
            RawValidator: Validator instance.
        """
        new_validator = RawValidator()
        new_validator.check_fn = lambda x: all(v.check_fn(x) for v in validators)
        return new_validator

    @staticmethod
    def any(validators):
        """
        Create a validator that requires any validator to pass.

        Args:
            validators (List[RawValidator]): List of validators.

        Returns:
            RawValidator: Validator instance.
        """
        new_validator = RawValidator()
        new_validator.check_fn = lambda x: any(v.check_fn(x) for v in validators)
        return new_validator

    def check(self, message: str) -> bool:
        """
        Check if a message passes the validator.

        Args:
            message (str): Message to validate.

        Returns:
            bool: True if the message passes, False otherwise.
        """
        return self.check_fn(message)

class Validator:
    """
    A high-level wrapper for RawValidator that provides message validation functionality.
    
    Example:
        ```python
        validator = Validator.starts_with("Hello")
        assert validator.check("Hello World") == True
        ```
    """
    
    def __init__(self):
        """
        Initialize a Validator with a RawValidator instance.
        """
        self._validator = RawValidator()
        
    @staticmethod
    def regex(pattern: str) -> 'Validator':
        """
        Create a Validator that checks if a string matches a regex pattern.

        Args:
            pattern (str): Regex pattern to match.

        Returns:
            Validator: Validator instance.
        """
        v = Validator()
        v._validator = RawValidator.regex(pattern)
        return v
        
    @staticmethod
    def starts_with(prefix: str) -> 'Validator':
        """
        Create a Validator that checks if a string starts with a prefix.

        Args:
            prefix (str): Prefix to check.

        Returns:
            Validator: Validator instance.
        """
        v = Validator()
        v._validator = RawValidator.starts_with(prefix)
        return v
        
    @staticmethod
    def ends_with(suffix: str) -> 'Validator':
        """
        Create a Validator that checks if a string ends with a suffix.

        Args:
            suffix (str): Suffix to check.

        Returns:
            Validator: Validator instance.
        """
        v = Validator()
        v._validator = RawValidator.ends_with(suffix)
        return v
        
    @staticmethod
    def contains(substring: str) -> 'Validator':
        """
        Create a Validator that checks if a string contains a substring.

        Args:
            substring (str): Substring to check.

        Returns:
            Validator: Validator instance.
        """
        v = Validator()
        v._validator = RawValidator.contains(substring)
        return v
        
    @staticmethod
    def json_field(field: str, value: any) -> 'Validator':
        """
        Create a Validator that checks if a JSON message contains a specific field with a value.

        Args:
            field (str): JSON field to check.
            value (any): Expected value of the field.

        Returns:
            Validator: Validator instance.
        """
        v = Validator()
        v._validator = RawValidator.json_field(field, value)
        return v
        
    @staticmethod
    def not_(validator: 'Validator') -> 'Validator':
        """
        Create a Validator that negates another Validator.

        Args:
            validator (Validator): Validator to negate.

        Returns:
            Validator: Validator instance.
        """
        v = Validator()
        v._validator = RawValidator.ne(validator._validator)
        return v
        
    @staticmethod
    def all(validators: List['Validator']) -> 'Validator':
        """
        Create a Validator that requires all Validators to pass.

        Args:
            validators (List[Validator]): List of Validators.

        Returns:
            Validator: Validator instance.
        """
        v = Validator()
        v._validator = RawValidator.all([v._validator for v in validators])
        return v
        
    @staticmethod
    def any(validators: List['Validator']) -> 'Validator':
        """
        Create a Validator that requires any Validator to pass.

        Args:
            validators (List[Validator]): List of Validators.

        Returns:
            Validator: Validator instance.
        """
        v = Validator()
        v._validator = RawValidator.any([v._validator for v in validators])
        return v
        
    def check(self, message: str) -> bool:
        """
        Check if a message passes the Validator.

        Args:
            message (str): Message to validate.

        Returns:
            bool: True if the message passes, False otherwise.
        """
        return self._validator.check(message)
        
    @property
    def raw_validator(self):
        """
        Get the underlying RawValidator.

        Returns:
            RawValidator: The RawValidator instance.
        """
        return self._validator
