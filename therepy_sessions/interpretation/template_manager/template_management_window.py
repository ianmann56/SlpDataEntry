import tkinter as tk
from tkinter import ttk, messagebox
from interpretation.template_manager.template_editor_window import TemplateEditorWindow
from interpretation.template_manager.template_creator_window import TemplateCreatorWindow
from interpretation.template_manager.student_data_sheet_template import StudentDataSheetTemplate


class DataSheetTemplateManagementWindow:
    """
    TKinter window for managing Student Data Sheet Templates.
    
    Provides functionality to:
    - Display a list of existing templates
    - Create new templates
    - Edit existing templates (opens separate windows)
    """
    
    def __init__(self, template_store, master, close_callback=None):
        """
        Initialize the template management window.
        
        Args:
            template_store (TemplateStore): Repository for template persistence operations
            master: Parent tkinter window
            close_callback: Optional callback function to call when window is closed
        """
        self.window = tk.Toplevel(master)
        
        self.template_store = template_store
        self.close_callback = close_callback
        
        self._setup_window()
        self._create_widgets()
        
    def _setup_window(self):
        """Configure the main window properties."""
        self.window.title("Data Sheet Template Management")
        self.window.geometry("600x400")
        self.window.resizable(True, True)
        
        # Handle window close event
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Center the window
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.window.winfo_screenheight() // 2) - (400 // 2)
        self.window.geometry(f"600x400+{x}+{y}")
        
    def _create_widgets(self):
        """Create and layout all the window widgets."""
        # Main container
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Title label
        title_label = ttk.Label(main_frame, text="Student Data Sheet Templates", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky=tk.W)
        
        # Templates list frame
        list_frame = ttk.LabelFrame(main_frame, text="Available Templates", padding="5")
        list_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # Listbox with scrollbar
        listbox_frame = ttk.Frame(list_frame)
        listbox_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        listbox_frame.columnconfigure(0, weight=1)
        listbox_frame.rowconfigure(0, weight=1)
        
        self.templates_listbox = tk.Listbox(listbox_frame, height=10)
        self.templates_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar for listbox
        scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.templates_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.templates_listbox.configure(yscrollcommand=scrollbar.set)
        
        # Bind double-click event
        self.templates_listbox.bind("<Double-Button-1>", self._on_template_double_click)
        
        # Populate listbox
        self._populate_templates_list()
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        # Create button
        create_button = ttk.Button(button_frame, text="Create New Template", 
                                  command=self._on_create_template)
        create_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Edit button
        edit_button = ttk.Button(button_frame, text="Edit Selected", 
                                command=self._on_edit_template)
        edit_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Delete button
        delete_button = ttk.Button(button_frame, text="Delete Selected", 
                                  command=self._on_delete_template)
        delete_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Close button
        close_button = ttk.Button(button_frame, text="Close", 
                                 command=self._on_close)
        close_button.pack(side=tk.RIGHT)
        
    def _populate_templates_list(self):
        """Populate the listbox with available templates."""
        self.templates_listbox.delete(0, tk.END)
        templates = self.template_store.get_all_templates()
        for template in templates:
            display_text = f"{template.name} (ID: {template.id})"
            self.templates_listbox.insert(tk.END, display_text)
            
    def _get_selected_template(self):
        """Get the currently selected template."""
        selection = self.templates_listbox.curselection()
        if not selection:
            return None
        index = selection[0]
        templates = self.template_store.get_all_templates()
        return templates[index] if index < len(templates) else None
        
    def _on_template_double_click(self, event):
        """Handle double-click on template list item."""
        self._on_edit_template()
        
    def _on_create_template(self):
        """Handle create new template button click."""
        # Open template creation window
        creator_window = TemplateCreatorWindow(self.window, self.template_store, self._on_template_saved)
        
    def _on_edit_template(self):
        """Handle edit template button click."""
        template = self._get_selected_template()
        if template is None:
            messagebox.showwarning("No Selection", "Please select a template to edit.")
            return
            
        # TODO: Open template editing window
        self._open_template_editor_window(template, f"Edit Template: {template.name}")
        
    def _on_delete_template(self):
        """Handle delete template button click."""
        template = self._get_selected_template()
        if template is None:
            messagebox.showwarning("No Selection", "Please select a template to delete.")
            return
            
        # Confirm deletion
        result = messagebox.askyesno("Confirm Delete", 
                                   f"Are you sure you want to delete the template '{template.name}'?")
        if result:
            # Delete from template store
            if self.template_store.delete_template(template.id):
                self._populate_templates_list()
                messagebox.showinfo("Deleted", f"Template '{template.name}' has been deleted.")
            else:
                messagebox.showerror("Error", f"Failed to delete template '{template.name}'.")
            
    def _open_template_editor_window(self, template, title):
        """
        Open the template editor window (stubbed for now).
        
        Args:
            template: StudentDataSheetTemplate to edit, or None for new template
            title: Window title
        """
        # Create a new window for template editing
        editor_window = TemplateEditorWindow(self.window, template, title, self.template_store, self._on_template_saved)
        
    def show(self):
        """Display the window and focus it."""
        self.window.focus_set()
            
    def _on_template_saved(self):
        """Callback method called when a template is saved from the editor."""
        # Refresh the template list to show any changes
        self._populate_templates_list()
        
    def _on_close(self):
        """Handle window close button click."""
        # Notify caller via callback if provided
        if self.close_callback:
            self.close_callback()
        self.window.destroy()
            

