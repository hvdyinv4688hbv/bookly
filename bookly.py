# PDF Quiz Application - Complete Single File
import flet as ft
import fitz  # PyMuPDF
import spacy
import json
import time
import os
import random
import threading
from collections import Counter

# ============================================================================
# THREAD-SAFE NLP PROCESSING
# ============================================================================

# Global thread-local storage for spaCy models
_thread_local = threading.local()

def get_nlp_model():
    """Get or create a thread-local spaCy model."""
    if not hasattr(_thread_local, 'nlp'):
        try:
            _thread_local.nlp = spacy.load("en_core_web_sm")
        except OSError:
            raise RuntimeError("spaCy model 'en_core_web_sm' not found. Please install it with: python -m spacy download en_core_web_sm")
    return _thread_local.nlp

def extract_text_from_pdf(pdf_doc, start_page: int, end_page: int) -> str:
    """Extracts text from a given page range of a PyMuPDF document object."""
    try:
        full_text = "".join([pdf_doc[p-1].get_text("text") for p in range(start_page, end_page + 1)])
        return full_text
    except Exception as e:
        raise RuntimeError(f"Failed to extract text from PDF: {e}")

"""def summarize_text(text: str, num_sentences: int = 3) -> str:
    """"""Generates a summary of the given text.""""""
    if not text.strip():
        return "No text provided for summarization."
    
    try:
        nlp = get_nlp_model()
        doc = nlp(text)
        
        keywords = [token.text for token in doc if not token.is_stop and not token.is_punct]
        if not keywords:
            return "Could not generate a summary from the provided text. It may be too short."
            
        freq = Counter(keywords)
        max_freq = max(freq.values())
        
        sent_strength = {}
        for sent in doc.sents:
            for word in sent:
                if word.text in freq:
                    sent_strength[sent] = sent_strength.get(sent, 0) + (freq[word.text] / max_freq)

        if not sent_strength:
            return "Could not generate a summary. The text structure might be unusual."

        summary_sents = sorted(sent_strength, key=sent_strength.get, reverse=True)[:num_sentences]
        summary = " ".join([sent.text.strip() for sent in summary_sents])
        
        return summary if summary else "Could not generate a summary from the provided text."
        
    except Exception as e:
        return f"Error generating summary: {e}"
"""
def generate_quiz_question(text: str) -> dict | None:
    """Generates a single multiple-choice question from the text."""
    if not text.strip():
        return None
        
    try:
        nlp = get_nlp_model()
        doc = nlp(text)
        
        # Try named entities first
        entities = [ent for ent in doc.ents if ent.label_ in ["PERSON", "GPE", "ORG", "PRODUCT", "LOC", "MONEY", "DATE", "TIME"]]
        unique_entities = list(set(ent.text.strip() for ent in entities if len(ent.text.strip()) > 1))
        
        # If not enough named entities, try important nouns
        if len(unique_entities) < 4:
            important_nouns = [token.text for token in doc if token.pos_ == "NOUN" and not token.is_stop and len(token.text) > 3]
            unique_entities = list(set(important_nouns))
        
        # If still not enough, try any significant words
        if len(unique_entities) < 4:
            significant_words = [token.text for token in doc if not token.is_stop and not token.is_punct and len(token.text) > 2]
            unique_entities = list(set(significant_words))
        
        if len(unique_entities) < 4:
            print(f"Not enough unique words found: {len(unique_entities)}")  # Debug
            return None
            
        correct_answer = random.choice(unique_entities)
        question_sentence = ""
        
        # Try to find a sentence containing the correct answer
        for sent in doc.sents:
            if correct_answer in sent.text and len(sent.text.split()) > 5:
                question_sentence = sent.text.replace(correct_answer, "_____")
                break
        
        # If no good sentence found, create a simple question
        if not question_sentence:
            question_sentence = f"What is the missing word: _____?"
                
        distractors = random.sample([e for e in unique_entities if e != correct_answer], 3)
        choices = distractors + [correct_answer]
        random.shuffle(choices)
        
        print(f"Generated quiz: {correct_answer} from {len(unique_entities)} options")  # Debug
        return {"question": question_sentence, "choices": choices, "answer": correct_answer}
        
    except Exception as e:
        print(f"Error generating quiz question: {e}")
        return None

# ============================================================================
# MAIN APPLICATION CLASS
# ============================================================================

path = 3  # define upfront so it can be used in the on_file_selected method

class PDFQuizApp:
    def __init__(self, page: ft.Page):
        # Page configuration
        self.page = page
        self.page.title = "PDF Master Tool"
        self.page.vertical_alignment = ft.MainAxisAlignment.START
        self.page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.padding = 20
        self.page.window_width = 1000
        self.page.window_height = 800

        # Application state
        self.pdf_doc = None
        self.extracted_text_content = ""
        self.scores = []
        self.scores_file = "quiz_scores.json"
        self.max_questions = 0
        self.quiz_timer = None  # Track timer for cleanup

        # UI Components - File Selection
        self.file_label = ft.Text("Hello!", italic=True, expand=True)
        self.file_path_entry = ft.TextField(label="Enter PDF file path", width=300, disabled=False)
        self.start_page_entry = ft.TextField(label="Start", width=100, disabled=True)
        self.end_page_entry = ft.TextField(label="End", width=100, disabled=True)
        self.extract_button = ft.ElevatedButton(
            "Extract Text", 
            on_click=self.extract_text_clicked, 
            disabled=True, 
            tooltip="Extract text from the selected page range"
        )
        
        # UI Components - Quiz Controls
        self.num_questions_entry = ft.TextField(
            label="Quiz Length", 
            value="5", 
            width=120, 
            text_align="center", 
            tooltip="Set the number of questions for the quiz"
        )
        self.start_quiz_button = ft.ElevatedButton(
            "Start Quiz", 
            on_click=self.start_quiz_clicked, 
            disabled=True, 
            height=40, 
            tooltip="Generate a quiz from the extracted text", 
            style=ft.ButtonStyle(bgcolor="blue700", color="white")
        )
        """self.summarize_button = ft.ElevatedButton(
            "Summarize", 
            on_click=self.summarize_text_clicked, 
            disabled=True, 
            height=40, 
            tooltip="Generate a summary of the extracted text"
        )"""
        
        # UI Components - Display Areas
        self.output_text_area = ft.TextField(
            label="Extracted Text appears here...", 
            multiline=True, 
            min_lines=15, 
            read_only=True, 
            expand=True
        )
        self.highest_score_label = ft.Text("Highest Score: N/A", size=18, weight=ft.FontWeight.BOLD)
        self.score_list_view = ft.ListView(expand=True, spacing=5, auto_scroll=True)
        
        # UI Components - Theme and File Picker
        self.theme_switcher = ft.Switch(
            label="Dark Mode", 
            value=False, 
            on_change=self.toggle_theme, 
            tooltip="Toggle light or dark theme"
        )
        #self.file_picker = ft.FilePicker(on_result=self.on_file_selected)
        #self.page.overlay.append(self.file_picker)

        # Initialize application
        self.load_scores()
        self.build_main_view()

    # ========================================================================
    # TEXT SUMMARIZATION METHODS
    # ========================================================================
    
    """def summarize_text_clicked(self, e):
        """"""Handle summarize button click with validation.""""""
        if not self.extracted_text_content.strip():
            self.show_error_dialog("No text to summarize.")
            return
        self.summarize_button.disabled = True
        self.summarize_button.text = "Summarizing..."
        self.page.update()
        threading.Thread(target=self.summarize_worker, daemon=True).start()

    def summarize_worker(self):
        """"""Background worker for text summarization.""""""
        try:
            print(f"Summarizing text of length: {len(self.extracted_text_content)}")  # Debug
            summary = summarize_text(self.extracted_text_content)
            print(f"Generated summary: {summary[:100]}...")  # Debug
            self.update_summary_ui(summary)
        except Exception as ex:
            print(f"Summarize error: {ex}")  # Debug
            self.update_summary_ui(f"An error occurred: {ex}", is_error=True)

    def update_summary_ui(self, summary_text, is_error=False):
        """"""Update UI with summarization results.""""""
        if is_error:
            self.show_error_dialog(summary_text)
        else:
            self.show_summary_dialog(summary_text)
        
        self.summarize_button.disabled = False
        self.summarize_button.text = "Summarize"
        self.page.update()

    def show_summary_dialog(self, summary_text):
        """"""Display summary in a modal dialog.""""""
        summary_content = ft.Container(
            width=550, height=400,
            content=ft.Column([ft.Text(summary_text, selectable=True)], scroll=ft.ScrollMode.ADAPTIVE)
        )
        self.page.dialog = ft.AlertDialog(
            modal=True, title=ft.Text("Text Summary"),
            content=summary_content,
            actions=[ft.TextButton("Close", on_click=lambda _: self.close_dialog())],
            actions_alignment="end"
        )
        self.page.dialog.open = True
        self.page.update()
    """

    # ========================================================================
    # QUIZ FUNCTIONALITY METHODS
    # ========================================================================
    
    def start_quiz_clicked(self, e):
        """Initialize and start a new quiz."""
        if len(self.extracted_text_content.strip()) < 200:
            self.show_error_dialog("Please extract more text for a good quiz.")
            return
        try:
            num_q = int(self.num_questions_entry.value)
            if num_q <= 0: 
                raise ValueError
            self.max_questions = num_q
        except ValueError:
            self.show_error_dialog("Please enter a valid, positive number for the quiz length.")
            return
        
        self.quiz_score, self.quiz_questions_asked = 0, 0
        self.build_quiz_view()
        self.generate_and_display_mcq()

    def check_quiz_answer(self, e):
        """Check user's quiz answer and provide feedback."""
        print(f"Submit button clicked! Selected: {self.quiz_choices_group.value}, Correct: {self.quiz_correct_answer}")  # Debug
        self.quiz_submit_button.disabled = True
        self.quiz_questions_asked += 1
        
        if self.quiz_choices_group.value == self.quiz_correct_answer:
            self.quiz_score += 1
            self.quiz_feedback_label.value, self.quiz_feedback_label.color = "Correct!", "green"
        else:
            self.quiz_feedback_label.value, self.quiz_feedback_label.color = f"Answer: {self.quiz_correct_answer}", "red"
        
        self.page.update()
        
        # Cancel any existing timer and start new one
        if self.quiz_timer:
            self.quiz_timer.cancel()
        self.quiz_timer = threading.Timer(2.0, self.generate_and_display_mcq)
        self.quiz_timer.start()

    def generate_and_display_mcq(self):
        """Generate and display the next quiz question."""
        if self.quiz_questions_asked >= self.max_questions:
            message = f"Quiz complete! You reached your goal of {self.max_questions} questions.\n\nFinal Score: {self.quiz_score} / {self.max_questions}"
            self.show_error_dialog(message, title="Quiz Finished!")
            self.end_quiz_clicked(None)
            return
            
        self.quiz_feedback_label.value, self.quiz_submit_button.disabled = "", False
        self.quiz_score_label.value = f"Score: {self.quiz_score} | Question: {self.quiz_questions_asked + 1} of {self.max_questions}"
        
        print(f"Generating quiz question from text of length: {len(self.extracted_text_content)}")  # Debug
        question_data = generate_quiz_question(self.extracted_text_content)
        print(f"Quiz question data: {question_data}")  # Debug
        
        if question_data:
            # Truncate very long questions but preserve blanks
            question_text = question_data["question"]
            if len(question_text) > 200:
                # Find the last blank and truncate after it if possible
                last_blank = question_text.rfind("_____")
                if last_blank > 150:  # If blank is in the last 50 chars, keep it
                    question_text = question_text[:last_blank + 5] + "..."
                else:
                    question_text = question_text[:200] + "..."
            
            # Make blanks more visible by using a different format
            question_text = question_text.replace("_____", "[_____]")
            print(f"Final question text: '{question_text}'")  # Debug
            self.quiz_question_label.value = question_text
            
            # Clear and rebuild the radio group
            self.quiz_choices_group.content.controls.clear()
            for choice in question_data["choices"]:
                # Create radio button with proper text wrapping
                radio_button = ft.Radio(
                    value=choice, 
                    label=choice,
                    label_style=ft.TextStyle(
                        size=14,
                        weight=ft.FontWeight.NORMAL
                    )
                )
                # Wrap the radio button in a container for better text handling
                wrapped_choice = ft.Container(
                    content=radio_button,
                    padding=ft.padding.symmetric(horizontal=10, vertical=5),
                    width=750,  # Fixed width to prevent overflow
                    border=ft.border.all(1, ft.Colors.GREY_200),
                    border_radius=5,
                    bgcolor=ft.Colors.WHITE,
                    margin=ft.margin.symmetric(vertical=2)
                )
                self.quiz_choices_group.content.controls.append(wrapped_choice)
            self.quiz_correct_answer = question_data["answer"]
            print("Quiz question displayed successfully")  # Debug
        else:
            print("No quiz question generated - not enough named entities")  # Debug
            message = f"The quiz has ended after {self.quiz_questions_asked} questions because the app could not find enough unique content to generate more.\n\nFinal Score: {self.quiz_score} / {self.quiz_questions_asked}"
            self.show_error_dialog(message, title="Quiz Content Exhausted")
            self.end_quiz_clicked(None)
        
        self.page.update()

    def end_quiz_clicked(self, e):
        """End the current quiz and return to main view."""
        # Cancel any pending timer
        if self.quiz_timer:
            self.quiz_timer.cancel()
            self.quiz_timer = None
            
        score_str = f"{self.quiz_score} / {self.quiz_questions_asked}" if self.quiz_questions_asked > 0 else None
        self.handle_quiz_end(score_str)

    # ========================================================================
    # SCORE MANAGEMENT METHODS
    # ========================================================================
    
    def get_highest_score(self):
        """Get the highest score from the scores list."""
        if not self.scores: 
            return "N/A"
        try: 
            return max(self.scores, key=lambda s: int(s.split('/')[0].strip()))
        except (ValueError, IndexError): 
            return "N/A"
    
    def load_scores(self):
        """Load quiz scores from file."""
        try:
            if os.path.exists(self.scores_file):
                with open(self.scores_file, "r") as f: 
                    self.scores = json.load(f)
            else: 
                self.scores = []
            self.update_score_display()
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading scores: {e}")
            self.scores = []

    def save_scores(self):
        """Save quiz scores to file."""
        try:
            with open(self.scores_file, "w") as f: 
                json.dump(self.scores, f, indent=4)
        except IOError as e:
            print(f"Error saving scores: {e}")
        
    def update_score_display(self):
        """Update the score display in the UI."""
        self.highest_score_label.value = f"Highest Score: {self.get_highest_score()}"
        self.score_list_view.controls.clear()
        for score in reversed(self.scores[-10:]):
            self.score_list_view.controls.append(ft.Text(f"• Score: {score}", size=14))

    def handle_quiz_end(self, final_score):
        """Handle quiz completion and score saving."""
        if final_score:
            self.scores.append(final_score)
            self.save_scores()
            self.update_score_display()
        self.build_main_view()

    # ========================================================================
    # UI BUILDING METHODS
    # ========================================================================
    
    def build_main_view(self):
        """Build and display the main application view."""
        self.page.controls.clear()
        self.page.add(
            ft.Column(
                [
                    ft.Row([
                        ft.Text("Bookly", size=32, weight=ft.FontWeight.BOLD, expand=True), 
                        self.theme_switcher
                    ]),
                    ft.Row([
                        ft.ElevatedButton(
                            "Press this button for fun"
                        ), 
                        self.file_label
                    ]),
                    ft.Row([
                        self.file_path_entry,
                        ft.ElevatedButton(
                            "Load from Path", 
                            on_click=self.load_from_path_clicked,
                            tooltip="Load PDF from file path"
                        )
                    ]),
                    ft.Row([self.start_page_entry, self.end_page_entry, self.extract_button]),
                    ft.Row([
                        self.num_questions_entry, 
                        self.start_quiz_button
                    ], alignment=ft.MainAxisAlignment.SPACE_AROUND),
                    ft.Divider(),
                    ft.Row(
                        [
                            ft.Column([
                                ft.Text("Extracted Text", weight=ft.FontWeight.BOLD), 
                                self.output_text_area
                            ], expand=3),
                            ft.Column([
                                self.highest_score_label, 
                                ft.Text("Recent Quiz Scores"), 
                                self.score_list_view
                            ], expand=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.START, 
                        expand=True
                    )
                ], expand=True,
            )
        )
        self.page.update()

    def build_quiz_view(self):
        """Build and display the quiz view."""
        self.page.controls.clear()
        self.quiz_score_label = ft.Text("Score: 0", size=24, weight=ft.FontWeight.BOLD)
        self.quiz_highest_score_label = ft.Text(f"High Score to Beat: {self.get_highest_score()}", italic=True)
        self.quiz_question_label = ft.Text("Loading...", size=16, text_align=ft.TextAlign.CENTER, width=800, max_lines=4, overflow=ft.TextOverflow.VISIBLE, selectable=True)
        self.quiz_choices_group = ft.RadioGroup(content=ft.Column(spacing=5))
        self.quiz_feedback_label = ft.Text("", size=16, weight=ft.FontWeight.BOLD)
        self.quiz_submit_button = ft.ElevatedButton("Submit", on_click=self.check_quiz_answer, tooltip="Submit your answer")
        print("Quiz view built - submit button created")  # Debug
        
        self.page.add(
            ft.Column(
                [
                    self.quiz_score_label, 
                    self.quiz_highest_score_label, 
                    ft.Divider(),
                    # Question container with fixed height and scrolling
                    ft.Container(
                        content=self.quiz_question_label,
                        padding=15,
                        width=800,
                        height=120,
                        border=ft.border.all(1, ft.Colors.GREY_300),
                        border_radius=5,
                        bgcolor=ft.Colors.GREY_50
                    ),
                    # Choices container with fixed height and scrolling
                    ft.Container(
                        content=ft.Column(
                            [self.quiz_choices_group],
                            scroll=ft.ScrollMode.ADAPTIVE,
                            spacing=5
                        ),
                        padding=15,
                        width=800,
                        height=250,
                        border=ft.border.all(1, ft.Colors.GREY_300),
                        border_radius=5,
                        bgcolor=ft.Colors.WHITE
                    ),
                    self.quiz_feedback_label,
                    # Fixed button row at bottom
                    ft.Container(
                        content=ft.Row([
                            self.quiz_submit_button, 
                            ft.ElevatedButton("End Quiz", on_click=self.end_quiz_clicked, tooltip="Finish the current quiz")
                        ], alignment=ft.MainAxisAlignment.CENTER, spacing=20),
                        padding=10,
                        width=800
                    )
                ], 
                horizontal_alignment=ft.CrossAxisAlignment.CENTER, 
                spacing=10,
                scroll=ft.ScrollMode.ADAPTIVE,
                expand=True
            )
        )
        self.page.update()

    def toggle_theme(self, e):
        """Toggle between light and dark themes."""
        self.page.theme_mode = ft.ThemeMode.DARK if self.theme_switcher.value else ft.ThemeMode.LIGHT
        self.theme_switcher.label = "Light Mode" if self.theme_switcher.value else "Dark Mode"
        self.page.update()

    # ========================================================================
    # FILE OPERATIONS METHODS
    # ========================================================================
    """
    path = 3  # define upfront so it can be used in the on_file_selected method
    def on_file_selected(self, e: ft.FilePickerResultEvent):
        
        """"""Handle PDF file selection.""""""
        print(f"File picker result: {e.files}")  # Debug
        if not e.files: 
            print("No files selected")  # Debug
            return
        try:
            # Handle both path and bytes for different Flet modes
            file_info = e.files[0]
            print(f"File info: {file_info}")  # Debug
            
            # Close existing PDF if open
            if self.pdf_doc: 
                print("Closing existing PDF")  # Debug
                self.pdf_doc.close()
            
            # Try to open PDF - handle both file path and bytes
            if hasattr(file_info, 'path') and file_info.path:
                # Desktop mode - use file path
                path = file_info.path
                print(path)
                if path == 3:
                    raise Exception("No valid file path found")
                print(f"Using file path: {path}")  # Debug
                self.pdf_doc = fitz.open(path)
                filename = os.path.basename(path)
            elif hasattr(file_info, 'bytes') and file_info.bytes:
                # Web mode - use bytes
                print(path)
                print("Using file bytes")  # Debug
                self.pdf_doc = fitz.open(stream=file_info.bytes, filetype="pdf")
                filename = file_info.name if hasattr(file_info, 'name') else "uploaded_file.pdf"
            else:
                print(path)
                raise Exception("No valid file path or bytes found")
            
            print(f"PDF opened successfully, pages: {self.pdf_doc.page_count}")  # Debug
            
            self.file_label.value = f"...{filename} ({self.pdf_doc.page_count} pages)"
            
            # Enable page range inputs
            for entry in [self.start_page_entry, self.end_page_entry]: 
                entry.disabled = False
            self.extract_button.disabled = False
            
            # Set default page range
            self.start_page_entry.value = "1"
            self.end_page_entry.value = str(self.pdf_doc.page_count)
            
            print("PDF selection completed successfully")  # Debug
        except Exception as ex: 
            print(path)
            print(f"Error in PDF selection: {ex}")  # Debug
            self.show_error_dialog(f"Failed to read PDF: {ex}")
        self.page.update()
    """

    def load_from_path_clicked(self, e):
        """Load PDF from manually entered file path."""
        path = self.file_path_entry.value.strip()
        if not path:
            self.show_error_dialog("Please enter a file path.")
            return
        
        if not os.path.exists(path):
            self.show_error_dialog(f"File not found: {path}")
            return
        
        if not path.lower().endswith('.pdf'):
            self.show_error_dialog("Please select a PDF file.")
            return
        
        try:
            # Close existing PDF if open
            if self.pdf_doc: 
                self.pdf_doc.close()
            
            self.pdf_doc = fitz.open(path)
            print(f"PDF loaded from path: {path}, pages: {self.pdf_doc.page_count}")
            
            self.file_label.value = f"...{os.path.basename(path)} ({self.pdf_doc.page_count} pages)"
            
            # Enable page range inputs
            for entry in [self.start_page_entry, self.end_page_entry]: 
                entry.disabled = False
            self.extract_button.disabled = False
            
            # Set default page range
            self.start_page_entry.value = "1"
            self.end_page_entry.value = str(self.pdf_doc.page_count)
            
        except Exception as ex: 
            print(f"Error loading PDF from path: {ex}")
            self.show_error_dialog(f"Failed to read PDF: {ex}")
        
        self.page.update()

    def extract_text_clicked(self, e):
        """Extract text from selected PDF pages."""
        if not self.pdf_doc: 
            return
        try:
            start, end = int(self.start_page_entry.value), int(self.end_page_entry.value)
            if not (1 <= start <= end <= self.pdf_doc.page_count):
                self.show_error_dialog(f"Page range must be 1-{self.pdf_doc.page_count}.")
                return
                
            self.output_text_area.value, self.output_text_area.disabled = f"Extracting pages {start}-{end}...", True
            self.page.update()
            
            full_text = extract_text_from_pdf(self.pdf_doc, start, end)
            self.output_text_area.value, self.output_text_area.disabled = full_text, False
            self.extracted_text_content = full_text
            
            # Enable buttons based on text content
            is_text_present = bool(full_text.strip())
            self.start_quiz_button.disabled = not is_text_present
            """self.summarize_button.disabled = not is_text_present"""
        except ValueError:
            self.show_error_dialog("Please enter valid page numbers.")
        except Exception as ex: 
            self.show_error_dialog(f"Extraction failed: {ex}")
        self.page.update()

    # ========================================================================
    # DIALOG AND ERROR HANDLING METHODS
    # ========================================================================
    
    def show_error_dialog(self, message, title="Error"):
        """Display an error dialog."""
        self.page.dialog = ft.AlertDialog(
            title=ft.Text(title), 
            content=ft.Text(message),
            actions=[ft.TextButton("OK", on_click=lambda _: self.close_dialog())], 
            actions_alignment="end"
        )
        self.page.dialog.open = True
        self.page.update()

    def close_dialog(self):
        """Close the current dialog."""
        self.page.dialog.open = False
        self.page.update()

    def __del__(self):
        """Cleanup when object is destroyed."""
        if self.pdf_doc:
            self.pdf_doc.close()
        if self.quiz_timer:
            self.quiz_timer.cancel()

# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

def main(page: ft.Page):
    """Main application entry point."""
    PDFQuizApp(page)

if __name__ == "__main__":
    # Use web browser mode for better compatibility
    print("Starting PDF Quiz App in web browser mode...")
    print("If you have issues with file selection, use the manual file path option.")
    ft.app(target=main, view=ft.WEB_BROWSER)
