import os

class TemplateProcessor:
    """
    Handles template processing and variable substitution.
    Provides methods to process strings, dictionaries, and files.
    """
    
    def __init__(self, template_functions, base_vars=None):
        """
        Initialize the template processor.
        
        Args:
            template_functions (dict): Map of function names to callables
            base_vars (dict): Base variables to use for substitution
        """
        self.functions = template_functions
        self.base_vars = base_vars or {}
    
    def ensure_path_variables(self, text, category=None, service_name=None, base_path=None):
        """
        Ensure Docker Compose path variables are replaced with actual values.
        
        Args:
            text (str): String to process
            category (str): Category name
            service_name (str): Service name
            base_path (str): Base path
            
        Returns:
            str: Processed string with path variables replaced
        """
        if not isinstance(text, str):
            return text
            
        # Set default values if not provided
        base_path = base_path or "/root"
        category = category or ""
        service_name = service_name or ""
        
        # Replace Docker Compose environment variables with actual values
        result = text
        result = result.replace("${BASE_PATH}", base_path)
        result = result.replace("${CATEGORY}", category)
        result = result.replace("${SERVICE_NAME}", service_name)
        
        return result

    def process_string(self, text, extra_vars=None):
        """
        Process template placeholders in a string.
        
        Args:
            text (str): String to process
            extra_vars (dict): Additional variables to use
            
        Returns:
            str: Processed string
        """
        if not isinstance(text, str):
            return text
                
        vars_to_use = dict(self.base_vars)
        if extra_vars:
            vars_to_use.update(extra_vars)
        
        # Process function calls like {{func_name:param}}
        if text.startswith("{{") and text.endswith("}}"):
            func_call = text[2:-2].strip()

            # Split function name and parameters
            if ':' in func_call:
                func_name, func_params_str = func_call.split(':', 1)
                func_name = func_name.strip()
                
                # Split parameters, handling potential comma-separated values
                func_params = [param.strip() for param in func_params_str.split(',')]
            else:
                func_name = func_call
                func_params = []            
            
            
            if func_name in self.functions:
                function = self.functions[func_name]

                # Handle functions with multiple parameters
                try:
                    # Convert parameters to appropriate types if possible
                    converted_params = []
                    for param in func_params:
                        # Try to convert to int if possible
                        try:
                            converted_param = int(param)
                        except ValueError:
                            # If not an int, keep as string
                            converted_param = param
                        converted_params.append(converted_param)
                    
                    # Call function with converted parameters
                    return str(function(*converted_params))
                except TypeError:
                    # If function doesn't accept multiple parameters, fall back to single param
                    if func_params:
                        return str(function(func_params[0]))
                    else:
                        return str(function())
            else:
                return func_name
        
        # Process variable references like ${VAR_NAME}
        result = text
        for var_name, var_value in vars_to_use.items():
            placeholder = "${" + var_name + "}"
            if placeholder in result:
                # Important: Evaluate var_value if it's a function call
                value_to_use = var_value
                if isinstance(var_value, str) and var_value.startswith("{{") and var_value.endswith("}}"):
                    # Recursively process this as a function call
                    value_to_use = self.process_string(var_value, extra_vars)
                result = result.replace(placeholder, str(value_to_use))
        
        return result               
    


    
    def process_dict(self, data, extra_vars=None):
        """
        Process template placeholders in a dictionary recursively.
        
        Args:
            data (dict): Dictionary to process
            extra_vars (dict): Additional variables to use
            
        Returns:
            dict: Processed dictionary
        """
        if not data:
            return {}
            
        result = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self.process_string(value, extra_vars)
            elif isinstance(value, dict):
                result[key] = self.process_dict(value, extra_vars)
            elif isinstance(value, list):
                result[key] = self.process_list(value, extra_vars)
            else:
                result[key] = value
                
        return result
    
    def process_list(self, data, extra_vars=None):
        """
        Process template placeholders in a list recursively.
        
        Args:
            data (list): List to process
            extra_vars (dict): Additional variables to use
            
        Returns:
            list: Processed list
        """
        if not data:
            return []
            
        result = []
        
        for item in data:
            if isinstance(item, str):
                result.append(self.process_string(item, extra_vars))
            elif isinstance(item, dict):
                result.append(self.process_dict(item, extra_vars))
            elif isinstance(item, list):
                result.append(self.process_list(item, extra_vars))
            else:
                result.append(item)
                
        return result
    
    def process_file(self, file_path, output_path=None, extra_vars=None):
        """
        Process template placeholders in a file.
        
        Args:
            file_path (str): Path to the file to process
            output_path (str): Path to write the processed file (or None to return the content)
            extra_vars (dict): Additional variables to use
            
        Returns:
            str: Processed content (if output_path is None)
        """
        with open(file_path, 'r') as f:
            content = f.read()
        
        processed_content = self.process_string(content, extra_vars)
        
        if output_path:
            with open(output_path, 'w') as f:
                f.write(processed_content)
        else:
            return processed_content


