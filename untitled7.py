import fitz  # PyMuPDF
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.colorchooser import askcolor
import ast
import io

# Initialize main application window
root = tk.Tk()
root.title("Easy PDF Editor")
root.geometry("1200x900")

# Initialize global variables
pdf_document = None
pdf_page = None
current_image = None  # Reference to the current image

# Undo stack to keep track of changes
undo_stack = []

# Initialize tool mode
current_tool = 'text'  # Default tool

# Version and author information
app_version = "1.2"
app_author = "Coded by Ayman Muzzamail ©"

# Function to set the current tool
def set_tool(tool):
    global current_tool
    current_tool = tool

# Function to browse for a PDF file
def browse_pdf():
    global pdf_document, pdf_page, current_image, undo_stack
    file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
    if file_path:
        try:
            pdf_document = fitz.open(file_path)
            pdf_page = pdf_document[0]  # Load the first page
            load_pdf()
            # Clear the undo stack and save the initial state
            undo_stack = []
            save_undo_state()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open PDF:\n{e}")

# Function to load and render the PDF on the canvas
def load_pdf():
    global pdf_page, current_image
    if pdf_document is None or pdf_page is None:
        messagebox.showerror("Error", "No PDF loaded.")
        return
    try:
        # Render the PDF page to a pixmap
        pix = pdf_page.get_pixmap(dpi=150)
        img_data = pix.tobytes("ppm")
        img = tk.PhotoImage(data=img_data)
        # Clear the canvas
        pdf_canvas.delete("all")
        # Add the image to the canvas
        pdf_canvas.create_image(0, 0, image=img, anchor=tk.NW, tags="pdf_image")
        # Keep a reference to the image to prevent garbage collection
        current_image = img
        # Update the scroll region to match the image size
        pdf_canvas.config(scrollregion=(0, 0, pix.width, pix.height))
    except Exception as e:
        messagebox.showerror("Error", f"Failed to render PDF page:\n{e}")

# Function to handle mouse click for inserting text and opening the dialog
def on_mouse_click(event):
    if pdf_document is None or pdf_page is None:
        messagebox.showerror("Error", "No PDF loaded.")
        return
    # Get canvas coordinates accounting for scrolling
    canvas_x = pdf_canvas.canvasx(event.x)
    canvas_y = pdf_canvas.canvasy(event.y)

    # Create placeholder text
    text_item = pdf_canvas.create_text(
        canvas_x, canvas_y, 
        text="Your Text", 
        font=("Arial", 16), 
        fill="blue", 
        tags="inserted_text"
    )

    # Open the text formatting dialog
    open_text_format_dialog(text_item)

# Function to open the text formatting dialog
def open_text_format_dialog(text_item):
    if text_item is None:
        messagebox.showerror("Error", "Failed to create text placeholder.")
        return
    dialog = tk.Toplevel(root)
    dialog.title("Add Text and Formatting")
    dialog.grab_set()  # Make the dialog modal

    # Input fields for text
    tk.Label(dialog, text="Text:").grid(row=0, column=0, sticky='e', padx=5, pady=5)
    text_entry = tk.Entry(dialog, width=30)
    text_entry.grid(row=0, column=1, columnspan=2, padx=5, pady=5)

    # Font size selection
    tk.Label(dialog, text="Font Size:").grid(row=1, column=0, sticky='e', padx=5, pady=5)
    font_size_var = tk.StringVar(value="12")
    font_size_menu = tk.OptionMenu(dialog, font_size_var, "10", "12", "14", "16", "18", "20", "24", "30")
    font_size_menu.grid(row=1, column=1, columnspan=2, sticky='w', padx=5, pady=5)

    # Bold checkbox
    bold_var = tk.BooleanVar()
    bold_check = tk.Checkbutton(dialog, text="Bold", variable=bold_var)
    bold_check.grid(row=2, column=0, columnspan=3, sticky='w', padx=5, pady=5)

    # Text color selection
    tk.Label(dialog, text="Text Color:").grid(row=3, column=0, sticky='e', padx=5, pady=5)
    color_button = tk.Button(dialog, text="Choose Color", command=lambda: select_color(color_var))
    color_button.grid(row=3, column=1, sticky='w', padx=5, pady=5)
    color_var = tk.StringVar(value="(0, 0, 0)")  # Default black

    def submit_text():
        # Get the selected text options
        text = text_entry.get().strip()
        font_size = font_size_var.get()
        bold = bold_var.get()
        color_str = color_var.get()

        if not text:
            messagebox.showerror("Input Error", "Text cannot be empty.")
            return

        try:
            font_size = int(font_size)
            if font_size <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Input Error", "Font size must be a positive integer.")
            return

        try:
            color = ast.literal_eval(color_str)
            if not (isinstance(color, tuple) and len(color) == 3):
                raise ValueError
        except (ValueError, SyntaxError):
            messagebox.showerror("Input Error", "Selected color is invalid.")
            return

        finalize_text(text, font_size, bold, color, text_item)
        dialog.destroy()

    submit_button = tk.Button(dialog, text="Submit", command=submit_text)
    submit_button.grid(row=4, column=0, columnspan=3, pady=10)

# Function to select text color using a color chooser
def select_color(color_var):
    color = askcolor()[0]  # Choose color, returns RGB tuple
    if color:
        # Convert color to a tuple of integers
        color_int = tuple(map(int, color))
        color_var.set(str(color_int))  # Store color in variable as string

# Function to finalize and insert the text into the PDF
def finalize_text(text, font_size, bold, color, text_item):
    global pdf_page
    if pdf_document is None or pdf_page is None:
        messagebox.showerror("Error", "No PDF loaded.")
        return

    # Save current state before inserting text
    save_undo_state()

    # Convert canvas coordinates to PDF coordinates
    canvas_x, canvas_y = pdf_canvas.coords(text_item)
    pdf_x, pdf_y = convert_canvas_to_pdf_coords(canvas_x, canvas_y)

    # Choose the correct font based on bold selection
    font_name = "helvB" if bold else "helv"

    # Insert the text into the PDF at the correct PDF coordinates
    try:
        pdf_page.insert_text(
            (pdf_x, pdf_y),
            text,
            fontsize=font_size,
            fontname=font_name,
            color=color,
            render_mode=0,  # Fill text
            rotate=0
        )
    except Exception as e:
        messagebox.showerror("Error", f"Failed to insert text into PDF:\n{e}")
        # Remove the placeholder text since it failed to insert
        pdf_canvas.delete(text_item)
        return

    # Reload the PDF to reflect changes
    load_pdf()

    # Remove the placeholder text
    if text_item:
        pdf_canvas.delete(text_item)

# Function to convert canvas coordinates to PDF coordinates
def convert_canvas_to_pdf_coords(canvas_x, canvas_y):
    if pdf_page is None:
        return 0, 0
    pdf_width = pdf_page.rect.width
    pdf_height = pdf_page.rect.height
    # Get the actual rendered image size from scrollregion
    scroll_region = pdf_canvas.cget("scrollregion")
    if not scroll_region:
        return 0, 0
    scroll_region = scroll_region.split()
    if len(scroll_region) != 4:
        return 0, 0
    scroll_width = int(scroll_region[2])
    scroll_height = int(scroll_region[3])
    # Convert canvas coordinates to PDF coordinates
    pdf_x = (canvas_x / scroll_width) * pdf_width
    pdf_y = (canvas_y / scroll_height) * pdf_height
    return pdf_x, pdf_y

# Function to save the edited PDF
def save_pdf():
    if pdf_document is None:
        messagebox.showerror("Error", "No PDF loaded.")
        return
    try:
        save_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")]
        )
        if save_path:
            pdf_document.save(save_path)
            messagebox.showinfo("Saved", "PDF saved successfully!")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save PDF:\n{e}")

# Function to save the undo state by saving the PDF into memory
def save_undo_state():
    global pdf_document, undo_stack
    if pdf_document:
        pdf_bytes = io.BytesIO()
        pdf_document.save(pdf_bytes)
        undo_stack.append(pdf_bytes.getvalue())
        # Limit the undo stack size to prevent excessive memory usage
        max_undo = 20  # Adjust as needed
        if len(undo_stack) > max_undo:
            undo_stack.pop(0)

# Function to undo the last change
def undo():
    global pdf_document, pdf_page, undo_stack
    if len(undo_stack) <= 1:
        messagebox.showinfo("Undo", "No actions to undo.")
        return

    # Remove the current state
    undo_stack.pop()

    # Get the last saved state
    last_state = undo_stack[-1]

    # Close the current document
    pdf_document.close()

    # Load the PDF from the last state
    pdf_bytes = io.BytesIO(last_state)
    pdf_document = fitz.open("pdf", pdf_bytes.getvalue())
    pdf_page = pdf_document[0]
    load_pdf()

# Function to erase directly on the PDF
def erase(event):
    global pdf_page
    if pdf_document is None or pdf_page is None:
        messagebox.showerror("Error", "No PDF loaded.")
        return

    # Save current state before erasing
    save_undo_state()

    # Get the canvas coordinates where the erase was initiated
    canvas_x = pdf_canvas.canvasx(event.x)
    canvas_y = pdf_canvas.canvasy(event.y)
    pdf_x, pdf_y = convert_canvas_to_pdf_coords(canvas_x, canvas_y)

    # Define the circle for erasing
    radius = eraser_size  # Use the global eraser size
    try:
        # Apply erasure directly to the PDF by drawing a filled white circle
        pdf_page.draw_circle(center=(pdf_x, pdf_y), radius=radius, color=(1, 1, 1), fill=(1, 1, 1))
    except Exception as e:
        messagebox.showerror("Error", f"Failed to erase content from PDF:\n{e}")

    # Reload the PDF to reflect changes
    load_pdf()

# Variables to track drawing state
is_drawing = False
current_line = None

# Function to handle mouse down based on the current tool
def on_mouse_down(event):
    global is_drawing, current_line
    if current_tool == 'draw':
        is_drawing = True
        canvas_x = pdf_canvas.canvasx(event.x)
        canvas_y = pdf_canvas.canvasy(event.y)
        # Start a new line
        current_line = pdf_canvas.create_line(canvas_x, canvas_y, canvas_x, canvas_y, fill="red", width=2, tags="drawn_line")
    elif current_tool == 'erase':
        erase(event)
    elif current_tool == 'text':
        on_mouse_click(event)

# Function to handle mouse movement based on the current tool
def on_mouse_move(event):
    global is_drawing, current_line
    if current_tool == 'draw' and is_drawing and current_line:
        canvas_x = pdf_canvas.canvasx(event.x)
        canvas_y = pdf_canvas.canvasy(event.y)
        # Append the new point to the line
        pdf_canvas.coords(current_line, *pdf_canvas.coords(current_line), canvas_x, canvas_y)
    elif current_tool == 'erase':
        erase(event)

# Function to handle mouse release based on the current tool
def on_mouse_up(event):
    global is_drawing, current_line
    if current_tool == 'draw' and is_drawing:
        is_drawing = False
        if current_line:
            # Store the line's coordinates for PDF annotation
            line_coords = pdf_canvas.coords(current_line)
            if len(line_coords) >= 4:
                drawn_lines.append(line_coords)
            current_line = None

# Function to display Help information
def show_help():
    help_window = tk.Toplevel(root)
    help_window.title("Help - Easy PDF Editor")
    help_window.geometry("600x400")
    help_window.grab_set()  # Make the window modal

    # Create a Text widget to display help content
    help_text = tk.Text(help_window, wrap=tk.WORD, padx=10, pady=10)
    help_text.pack(expand=True, fill=tk.BOTH)

    # Help content
    help_content = f"""
Welcome to Easy PDF Editor!

Version: {app_version}
{app_author}

This application allows you to edit PDF files with ease. Below are instructions on how to use the various features:

1. **Browse PDF**:
   - Click the "Browse PDF" button to select a PDF file to edit.

2. **Tools**:
   - **Text Tool**: Click on the "Text" button to activate the text tool. Click anywhere on the PDF to add text.
   - **Draw Tool**: Click on the "Draw" button to activate the draw tool. Click and drag on the PDF to draw lines.
   - **Erase Tool**: Click on the "Erase" button to activate the erase tool. Click and drag over the areas you want to erase.
     - Adjust the eraser size using the slider next to "Eraser Size".

3. **Undo**:
   - Click the "Undo" button to undo the last action.

4. **Save PDF**:
   - After making changes, click the "Save PDF" button to save your edited PDF.

**Note**:
- The "Undo" function allows you to revert your last action, whether it's adding text or erasing content.
- Make sure to save your work before closing the application.

**About**:
Easy PDF Editor is developed by Ayman Muzzamail. All rights reserved.

For any inquiries or support, please contact the developer.

Enjoy editing your PDFs!

"""

    # Insert help content into the Text widget
    help_text.insert(tk.END, help_content)
    help_text.configure(state='disabled')  # Make the text read-only

    # Add a Close button
    close_button = tk.Button(help_window, text="Close", command=help_window.destroy)
    close_button.pack(pady=10)

# Create a Frame to hold the Canvas and Scrollbars
canvas_frame = tk.Frame(root)
canvas_frame.pack(fill=tk.BOTH, expand=True)

# Create Canvas
pdf_canvas = tk.Canvas(canvas_frame, bg="grey")
pdf_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

# Create Vertical Scrollbar
v_scroll = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=pdf_canvas.yview)
v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

# Create Horizontal Scrollbar
h_scroll = tk.Scrollbar(root, orient=tk.HORIZONTAL, command=pdf_canvas.xview)
h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

# Configure Canvas to use Scrollbars
pdf_canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

# Toolbar Frame
toolbar_frame = tk.Frame(root, bd=1, relief=tk.RAISED)
toolbar_frame.pack(side=tk.TOP, fill=tk.X)

# Text Tool Button
text_tool_btn = tk.Button(toolbar_frame, text="Text", command=lambda: set_tool('text'))
text_tool_btn.pack(side=tk.LEFT, padx=2, pady=2)

# Draw Tool Button
draw_tool_btn = tk.Button(toolbar_frame, text="Draw", command=lambda: set_tool('draw'))
draw_tool_btn.pack(side=tk.LEFT, padx=2, pady=2)

# Erase Tool Button
erase_tool_btn = tk.Button(toolbar_frame, text="Erase", command=lambda: set_tool('erase'))
erase_tool_btn.pack(side=tk.LEFT, padx=2, pady=2)

# Eraser size (default value)
eraser_size = 10

# Eraser Size Slider
from tkinter import ttk
eraser_size_label = tk.Label(toolbar_frame, text="Eraser Size:")
eraser_size_label.pack(side=tk.LEFT, padx=2, pady=2)
eraser_size_slider = ttk.Scale(toolbar_frame, from_=5, to=50, orient=tk.HORIZONTAL, command=lambda val: set_eraser_size(val))
eraser_size_slider.set(eraser_size)
eraser_size_slider.pack(side=tk.LEFT, padx=2, pady=2)

def set_eraser_size(val):
    global eraser_size
    eraser_size = int(float(val))

# Button frame for actions
button_frame = tk.Frame(root)
button_frame.pack(fill=tk.X)

# Buttons for PDF operations
browse_button = tk.Button(button_frame, text="Browse PDF", command=browse_pdf)
browse_button.pack(side=tk.LEFT, padx=5, pady=5)

save_button = tk.Button(button_frame, text="Save PDF", command=save_pdf)
save_button.pack(side=tk.LEFT, padx=5, pady=5)

undo_button = tk.Button(button_frame, text="Undo", command=undo)
undo_button.pack(side=tk.LEFT, padx=5, pady=5)

# Help Button
help_button = tk.Button(button_frame, text="Help", command=show_help)
help_button.pack(side=tk.RIGHT, padx=5, pady=5)

# Bind mouse events to the canvas
pdf_canvas.bind("<ButtonPress-1>", on_mouse_down)
pdf_canvas.bind("<B1-Motion>", on_mouse_move)
pdf_canvas.bind("<ButtonRelease-1>", on_mouse_up)

# Start the application
root.mainloop()

