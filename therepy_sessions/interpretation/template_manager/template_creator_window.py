import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from interpretation.template_store import TemplateCreateDto
from interpretation.template_manager.interpreter_configs import DEFAULT_INTERPRETER_CONFIGS


class TemplateCreatorWindow:
    """
    TKinter window for creating new Student Data Sheet Templates.
    
    Provides a form interface for users to:
    - Enter template name
    - Select template file location
    - Configure template interpreter (stubbed for now)
    - Save the new template
    """
    
    def __init__(self, parent, template_store, save_callback, interpreter_configs=None):
        """
        Initialize the template creator window.
        
        Args:
            parent: Parent tkinter window
            template_store: TemplateStore for persistence operations
            save_callback: Callback function to call to update the parent when template is saved
            interpreter_configs: List of InterpreterConfig objects (defaults to DEFAULT_INTERPRETER_CONFIGS)
        """
        self.parent = parent
        self.template_store = template_store
        self.save_callback = save_callback
        self.interpreter_configs = interpreter_configs or DEFAULT_INTERPRETER_CONFIGS
        self.window = tk.Toplevel(parent)
        
        # Form field variables
        self.name_var = tk.StringVar()
        self.file_location_var = tk.StringVar()
        self.interpreters = []  # List to store multiple interpreters
        
        self._setup_window()
        self._create_form()
        self._setup_interpreter_configs()
        
    def _setup_window(self):
        """Configure the creator window properties."""
        self.window.title("Create New Template")
        self.window.geometry("500x500")
        self.window.resizable(True, True)
        
        # Make window modal
        self.window.transient(self.parent)
        self.window.grab_set()
        
        # Center relative to parent
        self.window.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (500 // 2)
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (400 // 2)
        self.window.geometry(f"500x500+{x}+{y}")
        
    def _create_form(self):
        """Create the template creation form."""
        self.main_frame = self._setup_main_container()
        self._create_title()
        self.form_frame = self._setup_form_container()
        self._create_template_name_field()
        self._create_file_location_field()
        self._create_interpreters_field()
        self._create_description_field()
        self._create_buttons()
        self._setup_key_bindings()
        
    def _setup_main_container(self):
        """Setup the main container frames."""
        # Top-level frame for theming
        top_frame = ttk.Frame(self.window)
        top_frame.pack(fill=tk.BOTH, expand=True)
        
        # Main container
        main_frame = ttk.Frame(top_frame, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        return main_frame
        
    def _create_title(self):
        """Create the form title."""
        title_label = ttk.Label(self.main_frame, text="Create New Template", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
    def _setup_form_container(self):
        """Setup the form fields container."""
        form_frame = ttk.Frame(self.main_frame)
        form_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Configure grid
        form_frame.columnconfigure(1, weight=1)
        form_frame.rowconfigure(3, weight=1)  # Make description field expandable
        
        return form_frame
        
    def _create_template_name_field(self):
        """Create the template name input field."""
        ttk.Label(self.form_frame, text="Template Name:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=(0, 10))
        name_entry = ttk.Entry(self.form_frame, textvariable=self.name_var, width=40)
        name_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        name_entry.focus()  # Set focus to first field
        
    def _create_file_location_field(self):
        """Create the file location input field with browse button."""
        ttk.Label(self.form_frame, text="File Location:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=(0, 10))
        
        file_frame = ttk.Frame(self.form_frame)
        file_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        file_frame.columnconfigure(0, weight=1)
        
        file_entry = ttk.Entry(file_frame, textvariable=self.file_location_var)
        file_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        browse_button = ttk.Button(file_frame, text="Browse...", command=self._browse_file)
        browse_button.grid(row=0, column=1)
        
    def _create_interpreters_field(self):
        """Create the interpreters management field."""
        ttk.Label(self.form_frame, text="Interpreters:").grid(row=2, column=0, sticky=(tk.W, tk.N), pady=5, padx=(0, 10))
        
        interpreters_frame = ttk.Frame(self.form_frame)
        interpreters_frame.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5)
        interpreters_frame.columnconfigure(0, weight=1)
        
        # Listbox to show current interpreters
        self.interpreters_listbox = tk.Listbox(interpreters_frame, height=4)
        self.interpreters_listbox.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # Interpreter type selection
        # Get interpreter names from injected configs
        interpreter_names = [config.name for config in self.interpreter_configs]
        self.interpreter_type_var = tk.StringVar(value=interpreter_names[0] if interpreter_names else "")
        interpreter_combo = ttk.Combobox(interpreters_frame, textvariable=self.interpreter_type_var,
                                        values=interpreter_names,
                                        state="readonly", width=25)
        interpreter_combo.grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        interpreter_combo.bind('<<ComboboxSelected>>', self._on_interpreter_type_changed)
        
        # Configuration frame for interpreter-specific fields
        self.config_frame = ttk.LabelFrame(interpreters_frame, text="Configuration", padding="5")
        self.config_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(5, 0))
        self.config_frame.columnconfigure(0, weight=1)
        
        # Initialize configuration widgets
        self._setup_interpreter_configs()
        # Initially show first available config
        if interpreter_names:
            self._show_config_for_type(interpreter_names[0])
        
        # Add and remove buttons
        button_frame = ttk.Frame(interpreters_frame)
        button_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(5, 0))
        
        add_interpreter_btn = ttk.Button(button_frame, text="Add Interpreter", command=self._add_interpreter)
        add_interpreter_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        remove_interpreter_btn = ttk.Button(button_frame, text="Remove Selected", command=self._remove_interpreter)
        remove_interpreter_btn.pack(side=tk.LEFT)
        
    def _create_description_field(self):
        """Create the description text field."""
        ttk.Label(self.form_frame, text="Description:").grid(row=3, column=0, sticky=(tk.W, tk.N), pady=5, padx=(0, 10))
        
        desc_frame = ttk.Frame(self.form_frame)
        desc_frame.grid(row=3, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        desc_frame.columnconfigure(0, weight=1)
        desc_frame.rowconfigure(0, weight=1)
        
        self.description_text = tk.Text(desc_frame, height=6, wrap=tk.WORD)
        self.description_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        desc_scrollbar = ttk.Scrollbar(desc_frame, orient=tk.VERTICAL, command=self.description_text.yview)
        desc_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.description_text.configure(yscrollcommand=desc_scrollbar.set)
        
    def _create_buttons(self):
        """Create the form action buttons."""
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(fill=tk.X)
        
        # Cancel button
        cancel_button = ttk.Button(button_frame, text="Cancel", command=self._on_cancel)
        cancel_button.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Create button
        create_button = ttk.Button(button_frame, text="Create Template", command=self._on_create)
        create_button.pack(side=tk.RIGHT)
        
    def _setup_key_bindings(self):
        """Setup keyboard shortcuts."""
        self.window.bind('<Return>', lambda e: self._on_create())
        
    def _browse_file(self):
        """Open file dialog to select template file location."""
        filename = filedialog.asksaveasfilename(
            title="Select Template File Location",
            defaultextension=".json",
            filetypes=[
                ("JSON files", "*.json"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.file_location_var.set(filename)
            
    def _validate_form(self):
        """
        Validate the form data.
        
        Returns:
            bool: True if form is valid, False otherwise
        """
        if not self.name_var.get().strip():
            messagebox.showerror("Validation Error", "Template name is required.")
            return False
            
        if not self.file_location_var.get().strip():
            messagebox.showerror("Validation Error", "File location is required.")
            return False
            
        if not self.interpreters:
            messagebox.showerror("Validation Error", "At least one interpreter must be added.")
            return False
            
        return True
        
    def _create_configured_interpreters(self):
        """
        Create configured interpreters based on the added types and their configurations.
        
        Returns:
            list: List of configured interpreter data with type and configuration
        """
        configured_interpreters = []
        
        for interpreter_type in self.interpreters:
            interpreter_config = {
                'type': interpreter_type,
                'configuration': {}
            }
            
            # Get the configuration for this interpreter type
            if interpreter_type in self.config_widgets:
                config_data = self.config_widgets[interpreter_type]['get_config']()
                interpreter_config['configuration'] = config_data
                    
            configured_interpreters.append(interpreter_config)
            
        return configured_interpreters
        
    def _on_create(self):
        """Handle create template button click."""
        if not self._validate_form():
            return
            
        try:
            # Create the DTO
            create_dto = TemplateCreateDto(
                name=self.name_var.get().strip(),
                file_location=self.file_location_var.get().strip(),
                configured_interpreter=self._create_configured_interpreters()
            )
            
            # Create the template via the store
            new_template = self.template_store.create_template(create_dto)
            
            # Show success message
            messagebox.showinfo("Success", f"Template '{new_template.name}' created successfully!")
            
            # Call the save callback to refresh the parent window
            if self.save_callback:
                self.save_callback()
                
            # Close the window
            self.window.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create template: {str(e)}")
            
    def _on_cancel(self):
        """Handle cancel button click."""
        # Check if there are unsaved changes
        has_changes = (
            self.name_var.get().strip() or 
            self.file_location_var.get().strip() or
            self.description_text.get("1.0", tk.END).strip() or
            self.interpreters
        )
        
        if has_changes:
            result = messagebox.askyesno("Confirm Cancel", 
                                       "You have unsaved changes. Are you sure you want to cancel?")
            if not result:
                return
                
        self.window.destroy()
        
    def _setup_interpreter_configs(self):
        """Setup configuration widgets for each injected interpreter type."""
        # Dictionary to store configuration widgets for each type
        self.config_widgets = {}
        
        # Create configuration widgets using injected configs
        for config in self.interpreter_configs:
            self.config_widgets[config.name] = config.create_config_form(self.config_frame)
        



        
    def _on_interpreter_type_changed(self, event=None):
        """Handle interpreter type selection change."""
        selected_type = self.interpreter_type_var.get()
        self._show_config_for_type(selected_type)
        
    def _show_config_for_type(self, interpreter_type):
        """Show configuration widgets for the selected interpreter type."""
        # Hide all config frames
        for config in self.config_widgets.values():
            config['frame'].grid_remove()
            
        # Show the selected config frame
        if interpreter_type in self.config_widgets:
            self.config_widgets[interpreter_type]['frame'].grid(row=0, column=0, sticky=(tk.W, tk.E))
        
    def _add_interpreter(self):
        """Add the selected interpreter type to the list."""
        interpreter_type = self.interpreter_type_var.get()
        if interpreter_type and interpreter_type not in self.interpreters:
            self.interpreters.append(interpreter_type)
            self._update_interpreters_list()
        elif interpreter_type in self.interpreters:
            messagebox.showwarning("Duplicate Interpreter", f"'{interpreter_type}' is already added.")
            
    def _remove_interpreter(self):
        """Remove the selected interpreter from the list."""
        selection = self.interpreters_listbox.curselection()
        if selection:
            index = selection[0]
            removed_interpreter = self.interpreters.pop(index)
            self._update_interpreters_list()
        else:
            messagebox.showwarning("No Selection", "Please select an interpreter to remove.")
            
    def _update_interpreters_list(self):
        """Update the interpreters listbox with current interpreters."""
        self.interpreters_listbox.delete(0, tk.END)
        for interpreter in self.interpreters:
            self.interpreters_listbox.insert(tk.END, interpreter)