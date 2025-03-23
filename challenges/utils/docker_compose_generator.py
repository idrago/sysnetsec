from .template_processor import TemplateProcessor
import os

class DockerComposeGenerator:
    """
    Generates Docker Compose configurations for CTF exercises.
    Handles both simple and composite services.
    """
    
    def __init__(self, config, template_processor):
        """
        Initialize the generator.
        
        Args:
            config (dict): Global configuration
            template_processor (TemplateProcessor): Template processor for variable substitution
        """
        self.config = config
        self.template_processor = template_processor
        self.network_name = config['network']['name']
    
    def generate(self, vm_config, category_name):
        """
        Generate a Docker Compose configuration for the given VM and category.
        
        Args:
            vm_config (dict): VM configuration
            category_name (str): Category name
            
        Returns:
            dict: Docker Compose configuration
        """
        # Create base compose configuration
        compose = {
            'networks': {
                self.network_name: {
                    'external': True  # Use existing network instead of creating a new one
                }
            },
            'services': {}
        }
        
        # Process each exercise
        for ex_id in vm_config['exercises']:
            ex_id = int(ex_id) if isinstance(ex_id, str) and ex_id.isdigit() else ex_id
            ex = self.config['exercises']['configs'].get(ex_id)
            if not ex:
                continue
                
            self._process_exercise(ex, compose, category_name)
            
        return compose
    
    def _process_exercise(self, ex, compose, category_name):
        """
        Process a single exercise and add it to the compose configuration.
        
        Args:
            ex (dict): Exercise configuration
            compose (dict): Docker Compose configuration
            category_name (str): Category name
        """
        service_name = ex['name']
        base_path = self.config['exercises']['base_path']
        
        # Get services definition
        services = self._get_services_definition(ex, service_name, category_name, base_path)
        
        # Add services to compose
        for svc_name, svc_config in services.items():
            compose['services'][svc_name] = svc_config
    
    def _get_services_definition(self, ex, service_name, category_name, base_path):
        """
        Get the services definition for an exercise.
        
        Args:
            ex (dict): Exercise configuration
            service_name (str): Service name
            category_name (str): Category name
            base_path (str): Base path
            
        Returns:
            dict: Services definition
        """
        # Process template variables
        template_vars = {}
        for key, value in ex.get('template_vars', {}).items():
            if isinstance(value, str):
                template_vars[key] = self.template_processor.process_string(value)
            else:
                template_vars[key] = value
                
        # Add common variables
        common_vars = {
            'BASE_PATH': base_path,
            'CATEGORY': category_name,
            'SERVICE_NAME': service_name
        }
        template_vars.update(common_vars)
        
        # Check if this is a composite service (multiple containers)
        if ex.get('composite_services', False) and 'services' in ex:
            return self._process_composite_services(ex, service_name, template_vars)
        else:
            return self._process_single_service(ex, service_name, template_vars)
    
    def _process_composite_services(self, ex, service_name, template_vars):
        """
        Process a composite service (multiple containers).
        
        Args:
            ex (dict): Exercise configuration
            service_name (str): Service name
            template_vars (dict): Template variables
            
        Returns:
            dict: Services definition
        """
        services = {}

        # Get default service config
        defaults = self.config.get('service_defaults', {})        
        
        # Get base path and category for path substitution
        base_path = self.config['exercises']['base_path']
        category = template_vars.get('CATEGORY', '')  # Use empty string if not provided
        
        # Process each service in the composite
        for sub_service_name, sub_service_config in ex['services'].items():
            # Create a deep copy to avoid modifying the original
            processed_config = self.template_processor.process_dict(sub_service_config, template_vars)

            # Apply default settings that aren't already defined
            for key, value in defaults.items():
                if key not in processed_config:
                    processed_config[key] = value            
            
            # Determine the full service name
            full_service_name = f"{service_name}_{sub_service_name}"
            
            # Set container name if not already set
            if 'container_name' not in processed_config:
                processed_config['container_name'] = full_service_name
                
            # Ensure network config exists
            if 'networks' not in processed_config:
                processed_config['networks'] = {self.network_name: {}}
            
            # Process any existing volumes to replace path variables
            if 'volumes' in processed_config:
                for i, volume in enumerate(processed_config['volumes']):
                    # Replace template path variables with actual values
                    volume = volume.replace("${BASE_PATH}", base_path)
                    volume = volume.replace("${CATEGORY}", category)
                    volume = volume.replace("${SERVICE_NAME}", service_name)
                    processed_config['volumes'][i] = volume
                    
            # Add to services
            services[full_service_name] = processed_config
            
        # Handle flag volume if needed
        if ex.get('deploy_flags', False):
            flag_service = ex.get('flag_service', list(ex['services'].keys())[0])
            flag_path = ex.get('flag_path', '/root/flag.txt')
            full_flag_service = f"{service_name}_{flag_service}"
            
            if full_flag_service in services:
                if 'volumes' not in services[full_flag_service]:
                    services[full_flag_service]['volumes'] = []
                
                # Use actual path values instead of variables
                flag_volume = f"{base_path}/{category}/{service_name}/flag/flag.txt:{flag_path}:ro"
                services[full_flag_service]['volumes'].append(flag_volume)
        
        return services
    
    def _process_single_service(self, ex, service_name, template_vars):
        """
        Process a single service.
        
        Args:
            ex (dict): Exercise configuration
            service_name (str): Service name
            template_vars (dict): Template variables
            
        Returns:
            dict: Services definition
        """
        # Get default service config
        defaults = self.config.get('service_defaults', {})
        
        # Create service configuration
        service = {}
        
        # Add defaults
        for key, value in defaults.items():
            service[key] = value
        
        # Basic service settings
        service['container_name'] = service_name
        service['hostname'] = service_name
        
        # Set build context
        if 'build' in ex:
            service['build'] = self.template_processor.process_string(ex['build'], template_vars)
        else:
            service['build'] = f"./{service_name}"
        
        # Network config
        if 'address' in ex:
            address = self.template_processor.process_string(ex['address'], template_vars)
            service['networks'] = {
                self.network_name: {
                    'ipv4_address': address.split('/')[0] if '/' in address else address
                }
            }
        else:
            service['networks'] = {self.network_name: {}}
        
        # Volumes for flag
        base_path = template_vars['BASE_PATH']
        category = template_vars['CATEGORY']
        
        # Add flag volume if deploying flags
        if ex.get('deploy_flags', True):
            flag_path = ex.get('flag_path', '/root/flag.txt')
            flag_volume = f"{base_path}/{category}/{service_name}/flag/flag.txt:{flag_path}:ro"
            service['volumes'].append(flag_volume)
        
        # Add exercise-specific volumes if defined
        if 'volumes' in ex:
            processed_volumes = []
            for volume in ex['volumes']:
                if isinstance(volume, str):
                    # Replace template variables
                    volume = self.template_processor.process_string(volume, template_vars)
                    # Also directly replace path variables
                    volume = volume.replace("${BASE_PATH}", base_path)
                    volume = volume.replace("${CATEGORY}", category)
                    volume = volume.replace("${SERVICE_NAME}", service_name)
                processed_volumes.append(volume)
            service['volumes'].extend(processed_volumes)
        
        # Add ports if defined
        if 'ports' in ex:
            service['ports'] = self.template_processor.process_list(ex['ports'], template_vars)
        
        # Add environment variables if defined
        if 'environment' in ex:
            service['environment'] = self.template_processor.process_list(ex['environment'], template_vars)
        
        # Add capability overrides if specified
        if 'cap_add' in ex:
            service['cap_add'] = ex['cap_add']
        
        return {service_name: service}