import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from interpretation.template_store import TemplateCreateDto


class TemplateCreatorWindow:
    """
    TKinter window for creating new Student Data Sheet Templates.
    
    Provides a form interface for users to:
    - Enter template name
    - Select template file location
    - Configure template interpreter (stubbed for now)
    - Save the new template
    """
    
    def __init__(self, parent, template_store, save_callback):
        """
        Initialize the template creator window.
        
        Args:
            parent: Parent tkinter window
            template_store: TemplateStore for persistence operations
            save_callback: Callback function to call to update the parent when template is saved
        """
        self.parent = parent
        self.template_store = template_store
        self.save_callback = save_callback
        self.window = tk.Toplevel(parent)
        
        # Form field variables
        self.name_var = tk.StringVar()
        self.file_location_var = tk.StringVar()
        self.interpreter_var = tk.StringVar(value="Table Interpreter")  # Default selection
        
        self._setup_window()
        self._create_form()
        
    def _setup_window(self):
        """Configure the creator window properties."""
        self.window.title("Create New Template")
        self.window.geometry("500x400")
        self.window.resizable(True, True)
        
        # Make window modal
        self.window.transient(self.parent)
        self.window.grab_set()
        
        # Center relative to parent
        self.window.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (500 // 2)
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (400 // 2)
        self.window.geometry(f"500x400+{x}+{y}")
        
    def _create_form(self):
        """Create the template creation form."""
        # Main container
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Create New Template", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Form fields frame
        form_frame = ttk.Frame(main_frame)
        form_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Configure grid
        form_frame.columnconfigure(1, weight=1)
        
        # Template Name
        ttk.Label(form_frame, text="Template Name:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=(0, 10))
        name_entry = ttk.Entry(form_frame, textvariable=self.name_var, width=40)
        name_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        name_entry.focus()  # Set focus to first field
        
        # File Location
        ttk.Label(form_frame, text="File Location:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=(0, 10))
        
        file_frame = ttk.Frame(form_frame)
        file_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        file_frame.columnconfigure(0, weight=1)
        
        file_entry = ttk.Entry(file_frame, textvariable=self.file_location_var)
        file_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        browse_button = ttk.Button(file_frame, text="Browse...", command=self._browse_file)
        browse_button.grid(row=0, column=1)
        
        # Interpreter Type
        ttk.Label(form_frame, text="Interpreter Type:").grid(row=2, column=0, sticky=tk.W, pady=5, padx=(0, 10))
        
        interpreter_combo = ttk.Combobox(form_frame, textvariable=self.interpreter_var, 
                                        values=["Table Interpreter", "Running Tally Interpreter", "Custom Interpreter"],
                                        state="readonly")
        interpreter_combo.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # Description (optional)
        ttk.Label(form_frame, text="Description:").grid(row=3, column=0, sticky=(tk.W, tk.N), pady=5, padx=(0, 10))
        
        desc_frame = ttk.Frame(form_frame)
        desc_frame.grid(row=3, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        desc_frame.columnconfigure(0, weight=1)
        desc_frame.rowconfigure(0, weight=1)
        
        self.description_text = tk.Text(desc_frame, height=6, wrap=tk.WORD)
        self.description_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        desc_scrollbar = ttk.Scrollbar(desc_frame, orient=tk.VERTICAL, command=self.description_text.yview)
        desc_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.description_text.configure(yscrollcommand=desc_scrollbar.set)
        
        # Configure form_frame row weights
        form_frame.rowconfigure(3, weight=1)
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        # Cancel button
        cancel_button = ttk.Button(button_frame, text="Cancel", command=self._on_cancel)
        cancel_button.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Create button
        create_button = ttk.Button(button_frame, text="Create Template", command=self._on_create)
        create_button.pack(side=tk.RIGHT)
        
        # Bind Enter key to create
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
            
        if not self.interpreter_var.get():
            messagebox.showerror("Validation Error", "Interpreter type must be selected.")
            return False
            
        return True
        
    def _create_configured_interpreter(self):
        """
        Create a configured interpreter based on the selected type.
        
        For now, this is stubbed and returns None.
        In a real implementation, this would create the appropriate interpreter
        based on the selected type and any additional configuration.
        
        Returns:
            object or None: The configured interpreter (currently None)
        """
        # TODO: Implement actual interpreter creation based on type
        # This would involve:
        # - Creating the appropriate interpreter class (TableInterpreter, RunningTallyInterpreter, etc.)
        # - Configuring it with the necessary parameters
        # - Returning the configured instance
        
        interpreter_type = self.interpreter_var.get()
        
        # Placeholder - return None for now
        # In future iterations, this will return actual interpreter instances
        return None
        
    def _on_create(self):
        """Handle create template button click."""
        if not self._validate_form():
            return
            
        try:
            # Create the DTO
            create_dto = TemplateCreateDto(
                name=self.name_var.get().strip(),
                file_location=self.file_location_var.get().strip(),
                configured_interpreter=self._create_configured_interpreter()
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
            self.description_text.get("1.0", tk.END).strip()
        )
        
        if has_changes:
            result = messagebox.askyesno("Confirm Cancel", 
                                       "You have unsaved changes. Are you sure you want to cancel?")
            if not result:
                return
                
        self.window.destroy()