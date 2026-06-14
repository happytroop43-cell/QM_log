import os
import sqlite3
import shutil
from datetime import datetime
import pandas as pd
import qrcode
import cv2
import webbrowser
from pyzbar.pyzbar import decode

# Kivy Imports
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.core.window import Window
from kivy.properties import BooleanProperty, ObjectProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout

# --- System Configuration ---
Window.size = (1100, 800)
Window.title = "QM_log: Logistics Command (Strelizia Engine)"
Window.clearcolor = (0.95, 0.95, 0.97, 1)

DB_NAME = "QM_log.db"
QR_DIR = "qrcodes"
TEMP_DIR = "temp_transactions"
REPORT_DIR = "reports"

for folder in [QR_DIR, TEMP_DIR, REPORT_DIR, 'data']:
    if not os.path.exists(folder): os.makedirs(folder)

# --- Database Setup ---
def setup_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY, name TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS items 
                      (qr_code TEXT PRIMARY KEY, part_number TEXT, description TEXT, 
                       category TEXT, status TEXT DEFAULT 'In Stock', is_perishable INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS people 
                      (person_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, details TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, qr_code TEXT, person_id INTEGER, 
                       action TEXT, timestamp DATETIME)''')
    
    cursor.execute("SELECT count(*) FROM categories")
    if cursor.fetchone()[0] == 0:
        defaults = [("NON PERISHABLE MACHINED OBJECTS",), ("PERISHABLE-NON-CHEMICAL",), ("CLEANING-MATERIALS",)]
        cursor.executemany("INSERT INTO categories (name) VALUES (?)", defaults)
        
    conn.commit()
    conn.close()

setup_database()

# --- Custom Hover Behavior & Widgets ---
class HoverBehavior(object):
    hovered = BooleanProperty(False)
    border_point = ObjectProperty(None)
    def __init__(self, **kwargs):
        self.register_event_type('on_enter')
        self.register_event_type('on_leave')
        Window.bind(mouse_pos=self.on_mouse_pos)
        super(HoverBehavior, self).__init__(**kwargs)

    def on_mouse_pos(self, *args):
        if not self.get_root_window(): return
        pos = args[1]
        inside = self.collide_point(*self.to_widget(*pos))
        if self.hovered == inside: return
        self.border_point = pos
        self.hovered = inside
        if inside: self.dispatch('on_enter')
        else: self.dispatch('on_leave')

    def on_enter(self): pass
    def on_leave(self): pass

class ModernButton(HoverBehavior, ButtonBehavior, Label):
    bg_color = ObjectProperty([0.2, 0.3, 0.4, 1])
    hover_color = ObjectProperty([0.3, 0.4, 0.5, 1])
    
class HoverListItem(HoverBehavior, BoxLayout):
    item_data = ObjectProperty(None)
    def on_enter(self):
        app = App.get_running_app()
        if hasattr(app.root.get_screen('catalog'), 'preview_qr'):
            app.root.get_screen('catalog').preview_qr(self.item_data)

# --- The Kivy UI Design (KV) ---
KV = '''
#:import hex kivy.utils.get_color_from_hex

<ModernButton>:
    canvas.before:
        Color:
            rgba: self.hover_color if self.hovered else self.bg_color
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [8]
    color: 1, 1, 1, 1
    bold: True
    font_size: dp(14)

<HoverListItem>:
    canvas.before:
        Color:
            rgba: (0.9, 0.95, 1, 1) if self.hovered else (1, 1, 1, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [5]
    padding: dp(10)
    spacing: dp(10)
    size_hint_y: None
    height: dp(50)
    Label:
        text: root.item_data.get('part_number', '') if root.item_data else ''
        color: 0.1, 0.1, 0.1, 1
        bold: True
    Label:
        text: root.item_data.get('category', '') if root.item_data else ''
        color: 0.4, 0.4, 0.4, 1

<Sidebar@BoxLayout>:
    orientation: 'vertical'
    size_hint_x: 0.25
    padding: dp(15)
    spacing: dp(15)
    canvas.before:
        Color:
            rgba: hex('#2C3E50')
        Rectangle:
            pos: self.pos
            size: self.size
            
    Label:
        text: "STRELIZIA\\nCOMMAND"
        bold: True
        font_size: dp(22)
        halign: 'center'
        size_hint_y: 0.15
        
    ModernButton:
        text: "Setup Wizard"
        bg_color: hex('#34495E')
        size_hint_y: 0.1
        on_release: app.root.current = 'wizard'
    ModernButton:
        text: "Daily Operations"
        bg_color: hex('#2980B9')
        size_hint_y: 0.1
        on_release: app.root.current = 'ops'
    ModernButton:
        text: "Catalog Manager"
        bg_color: hex('#27AE60')
        size_hint_y: 0.1
        on_release: app.root.current = 'catalog'
    ModernButton:
        text: "Personnel / HR"
        bg_color: hex('#D35400')
        size_hint_y: 0.1
        on_release: app.root.current = 'hr'
    ModernButton:
        text: "Analytics & Print"
        bg_color: hex('#8E44AD')
        size_hint_y: 0.1
        on_release: app.root.current = 'analytics'
    Widget:
        size_hint_y: 0.4

# (Wizard, Ops, Catalog, and HR Screens remain unchanged structurally, just utilizing the Sidebar)
<WizardScreen>:
    BoxLayout:
        Sidebar:
        BoxLayout:
            orientation: 'vertical'
            padding: dp(40)
            spacing: dp(20)
            Label:
                text: "Hello, welcome to QM_log.\\nHow can we assist you in building your inventory today?"
                color: hex('#2C3E50')
                font_size: dp(24)
                bold: True
                halign: 'center'
                size_hint_y: 0.2
            BoxLayout:
                orientation: 'horizontal'
                spacing: dp(20)
                size_hint_y: 0.6
                BoxLayout:
                    orientation: 'vertical'
                    spacing: dp(10)
                    Label:
                        text: "1. Select or Edit Category"
                        color: 0.2, 0.2, 0.2, 1
                        bold: True
                        size_hint_y: 0.1
                    ScrollView:
                        GridLayout:
                            id: category_grid
                            cols: 1
                            size_hint_y: None
                            height: self.minimum_height
                            spacing: dp(5)
                    TextInput:
                        id: new_cat_input
                        hint_text: "Add new category..."
                        size_hint_y: 0.15
                        multiline: False
                    ModernButton:
                        text: "Add Category"
                        size_hint_y: 0.15
                        bg_color: hex('#7F8C8D')
                        on_release: root.add_category()
                BoxLayout:
                    orientation: 'vertical'
                    spacing: dp(10)
                    Label:
                        text: "2. Choose Import Method"
                        color: 0.2, 0.2, 0.2, 1
                        bold: True
                        size_hint_y: 0.1
                    ModernButton:
                        text: "Import Excel via USB"
                        bg_color: hex('#27AE60')
                        size_hint_y: 0.2
                        on_release: root.trigger_usb_import()
                    ModernButton:
                        text: "Manual Spreadsheet Entry"
                        bg_color: hex('#2980B9')
                        size_hint_y: 0.2
                        on_release: root.open_manual_entry()
                    BoxLayout:
                        canvas.before:
                            Color:
                                rgba: 1, 1, 1, 1
                            RoundedRectangle:
                                pos: self.pos
                                size: self.size
                                radius: [10]
                        padding: dp(10)
                        Label:
                            id: wizard_display
                            text: "[System Status: Awaiting Input]"
                            color: 0.5, 0.5, 0.5, 1
                            halign: 'center'

<OpsScreen>:
    BoxLayout:
        Sidebar:
        BoxLayout:
            orientation: 'horizontal'
            padding: dp(20)
            spacing: dp(20)
            BoxLayout:
                orientation: 'vertical'
                size_hint_x: 0.6
                spacing: dp(15)
                Label:
                    text: "Daily Operations"
                    color: hex('#2C3E50')
                    font_size: dp(28)
                    bold: True
                    size_hint_y: 0.1
                TextInput:
                    id: scan_item
                    hint_text: "Scan Item QR"
                    size_hint_y: 0.15
                    multiline: False
                TextInput:
                    id: scan_user
                    hint_text: "Scan User QR"
                    size_hint_y: 0.15
                    multiline: False
                GridLayout:
                    cols: 2
                    spacing: dp(10)
                    size_hint_y: 0.2
                    ModernButton:
                        text: "Draw Item"
                        bg_color: hex('#E74C3C')
                        on_release: root.draw_item()
                    ModernButton:
                        text: "Return Item"
                        bg_color: hex('#27AE60')
                        on_release: root.return_item()
                TextInput:
                    id: console
                    readonly: True
                    text: "Ready for scans..."
                    background_color: 0.9, 0.9, 0.9, 1
            BoxLayout:
                orientation: 'vertical'
                size_hint_x: 0.4
                Label:
                    text: "Transaction Slip"
                    color: 0.2, 0.2, 0.2, 1
                    size_hint_y: 0.1
                Image:
                    id: transaction_qr
                    source: ''
                    allow_stretch: True

<CatalogScreen>:
    BoxLayout:
        Sidebar:
        BoxLayout:
            orientation: 'horizontal'
            padding: dp(20)
            spacing: dp(20)
            BoxLayout:
                orientation: 'vertical'
                size_hint_x: 0.6
                Label:
                    text: "Catalog Manager"
                    color: hex('#2C3E50')
                    font_size: dp(28)
                    bold: True
                    size_hint_y: 0.1
                ScrollView:
                    GridLayout:
                        id: inventory_list
                        cols: 1
                        size_hint_y: None
                        height: self.minimum_height
                        spacing: dp(2)
            BoxLayout:
                orientation: 'vertical'
                size_hint_x: 0.4
                canvas.before:
                    Color:
                        rgba: 1, 1, 1, 1
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                padding: dp(15)
                Image:
                    id: live_qr
                    source: ''
                    allow_stretch: True
                Label:
                    id: live_details
                    text: "Hover over item to view."
                    color: 0.2, 0.2, 0.2, 1
                    size_hint_y: 0.3

<HRScreen>:
    BoxLayout:
        Sidebar:
        BoxLayout:
            orientation: 'vertical'
            padding: dp(30)
            spacing: dp(15)
            Label:
                text: "Personnel Management"
                color: hex('#2C3E50')
                font_size: dp(28)
                bold: True
                size_hint_y: 0.1
            GridLayout:
                cols: 2
                spacing: dp(20)
                size_hint_y: 0.2
                TextInput:
                    id: hr_name
                    hint_text: "Full Name"
                    multiline: False
                ModernButton:
                    text: "Register & Generate QR"
                    bg_color: hex('#D35400')
                    on_release: root.register()
            TextInput:
                id: console
                readonly: True
                background_color: 0.9, 0.9, 0.9, 1

<AnalyticsScreen>:
    BoxLayout:
        Sidebar:
        BoxLayout:
            orientation: 'vertical'
            padding: dp(30)
            spacing: dp(20)
            Label:
                text: "Analytics & Export Command"
                color: hex('#2C3E50')
                font_size: dp(28)
                bold: True
                size_hint_y: 0.1
                
            GridLayout:
                cols: 2
                spacing: dp(15)
                size_hint_y: 0.4
                
                ModernButton:
                    text: "Analyze Outstanding Returns\\n(Generate Excel)"
                    halign: 'center'
                    bg_color: hex('#E74C3C')
                    on_release: root.analyze_missing()
                    
                ModernButton:
                    text: "Export Master Inventory\\n(Generate Excel)"
                    halign: 'center'
                    bg_color: hex('#2980B9')
                    on_release: root.export_master()
                    
                ModernButton:
                    text: "Print Personnel Slips\\n(Generates HTML to Print)"
                    halign: 'center'
                    bg_color: hex('#D35400')
                    on_release: root.print_qr_set('USER_')
                    
                ModernButton:
                    text: "Print Inventory QRs\\n(Generates HTML to Print)"
                    halign: 'center'
                    bg_color: hex('#27AE60')
                    on_release: root.print_qr_set('ITEM')
                    
            TextInput:
                id: console
                readonly: True
                text: "System Ready. Select an analysis or print operation."
                background_color: 0.9, 0.9, 0.9, 1
                size_hint_y: 0.5
'''

# Helper: Generate standard QR
def generate_qr(data, filename):
    safe = str(filename).replace('/', '_').replace('\\', '_')
    path = os.path.join(QR_DIR, f"{safe}.png")
    qr = qrcode.make(data)
    qr.save(path)
    return path

# --- Screen Logics ---
class WizardScreen(Screen):
    def on_enter(self): self.load_categories()
    def load_categories(self):
        self.ids.category_grid.clear_widgets()
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM categories")
        for row in cursor.fetchall():
            btn = ModernButton(text=row[0], size_hint_y=None, height=40, bg_color=(0.5, 0.6, 0.7, 1))
            btn.bind(on_release=lambda x, cat=row[0]: self.select_category(cat))
            self.ids.category_grid.add_widget(btn)
        conn.close()
    def select_category(self, cat_name):
        self.active_category = cat_name
        self.ids.wizard_display.text = f"Selected:\\n{cat_name}\\n\\nReady for Import or Entry."
    def add_category(self):
        new_cat = self.ids.new_cat_input.text.strip().upper()
        if new_cat:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO categories (name) VALUES (?)", (new_cat,))
            conn.commit()
            conn.close()
            self.ids.new_cat_input.text = ""
            self.load_categories()
    def trigger_usb_import(self):
        self.ids.wizard_display.text = f"[*] Import via USB triggered for {getattr(self, 'active_category', 'No Category')}."
    def open_manual_entry(self):
        self.ids.wizard_display.text = "[*] Launching Manual Spreadsheet Entry..."

class OpsScreen(Screen):
    def log(self, msg): self.ids.console.text = f"{msg}\n{self.ids.console.text}"
    def draw_item(self):
        item_qr = self.ids.scan_item.text.strip()
        user_qr = self.ids.scan_user.text.strip()
        if not item_qr or not user_qr: return
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT status, is_perishable FROM items WHERE qr_code = ?", (item_qr,))
        res = cursor.fetchone()
        if not res:
            self.log("[-] Item not found.")
        elif res[1] == 1:
            cursor.execute("DELETE FROM items WHERE qr_code = ?", (item_qr,))
            cursor.execute("INSERT INTO transactions (qr_code, person_id, action, timestamp) VALUES (?, ?, 'Scrubbed/Consumed', ?)",
                           (item_qr, user_qr, datetime.now()))
            self.log(f"[!] Perishable {item_qr} consumed by {user_qr}. Scrubbed.")
        else:
            cursor.execute("UPDATE items SET status = 'Drawn' WHERE qr_code = ?", (item_qr,))
            cursor.execute("INSERT INTO transactions (qr_code, person_id, action, timestamp) VALUES (?, ?, 'Drawn', ?)",
                           (item_qr, user_qr, datetime.now()))
            receipt_data = f"CHECKOUT|{item_qr}|{user_qr}"
            receipt_path = os.path.join(TEMP_DIR, f"RECEIPT_{item_qr}.png")
            qrcode.make(receipt_data).save(receipt_path)
            self.ids.transaction_qr.source = receipt_path
            self.ids.transaction_qr.reload()
            self.log(f"[+] ISSUED. Temporary bond created.")
        conn.commit()
        conn.close()
        self.ids.scan_item.text = ""

    def return_item(self):
        item_qr = self.ids.scan_item.text.strip()
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE items SET status = 'In Stock' WHERE qr_code = ?", (item_qr,))
        cursor.execute("INSERT INTO transactions (qr_code, action, timestamp) VALUES (?, 'Returned', ?)",
                       (item_qr, datetime.now()))
        conn.commit()
        conn.close()
        receipt_path = os.path.join(TEMP_DIR, f"RECEIPT_{item_qr}.png")
        if os.path.exists(receipt_path): os.remove(receipt_path)
        self.ids.transaction_qr.source = ''
        self.log(f"[+] RETURNED. Temp bond destroyed.")
        self.ids.scan_item.text = ""

class CatalogScreen(Screen):
    def on_enter(self): self.refresh_list()
    def refresh_list(self):
        self.ids.inventory_list.clear_widgets()
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT qr_code, part_number, category, status FROM items")
        for row in cursor.fetchall():
            item_data = {'qr_code': row[0], 'part_number': row[1], 'category': row[2], 'status': row[3]}
            widget = HoverListItem(item_data=item_data)
            self.ids.inventory_list.add_widget(widget)
        conn.close()
    def preview_qr(self, data):
        path = os.path.join(QR_DIR, f"{data['part_number']}.png")
        if os.path.exists(path):
            self.ids.live_qr.source = path
            self.ids.live_qr.reload()
            self.ids.live_details.text = f"Part: {data['part_number']}\nCat: {data['category']}\nStatus: {data['status']}"

class HRScreen(Screen):
    def log(self, msg): self.ids.console.text = f"{msg}\n{self.ids.console.text}"
    def register(self):
        name = self.ids.hr_name.text.strip()
        if name:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO people (name) VALUES (?)", (name,))
            pid = cursor.lastrowid
            conn.commit()
            conn.close()
            path = generate_qr(f"USER_{pid}", f"USER_{pid}_{name}")
            self.log(f"[+] HR Updated: {name}. QR generated at {path}")
            self.ids.hr_name.text = ""

class AnalyticsScreen(Screen):
    def log(self, msg):
        self.ids.console.text = f"{msg}\n{self.ids.console.text}"

    def analyze_missing(self):
        conn = sqlite3.connect(DB_NAME)
        query = '''
            SELECT i.part_number, i.description, i.category, t.person_id as drawn_by, MAX(t.timestamp) as date_drawn
            FROM items i
            JOIN transactions t ON i.qr_code = t.qr_code
            WHERE i.status = 'Drawn'
            GROUP BY i.qr_code
            ORDER BY t.timestamp ASC
        '''
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        filename = os.path.join(REPORT_DIR, f"Outstanding_Returns_{datetime.now().strftime('%Y%m%d')}.xlsx")
        df.to_excel(filename, index=False)
        self.log(f"[!] Analysis Complete. {len(df)} items outstanding. Saved to {filename}")

    def export_master(self):
        conn = sqlite3.connect(DB_NAME)
        df_items = pd.read_sql_query("SELECT * FROM items", conn)
        df_trans = pd.read_sql_query("SELECT * FROM transactions", conn)
        conn.close()
        
        filename = os.path.join(REPORT_DIR, f"Master_Log_{datetime.now().strftime('%Y%m%d')}.xlsx")
        with pd.ExcelWriter(filename) as writer:
            df_items.to_excel(writer, sheet_name='Current Stock', index=False)
            df_trans.to_excel(writer, sheet_name='Audit Ledger', index=False)
        self.log(f"[+] Master Export saved to {filename}")

    def print_qr_set(self, filter_str):
        # Generate an HTML file with images for native OS printing
        html_path = os.path.join(REPORT_DIR, "print_spool.html")
        files = [f for f in os.listdir(QR_DIR) if f.endswith('.png')]
        
        if filter_str == 'USER_':
            target_files = [f for f in files if f.startswith('USER_')]
            title = "Personnel Identification Slips"
        else:
            target_files = [f for f in files if not f.startswith('USER_')]
            title = "Inventory Assest QR Codes"

        if not target_files:
            self.log(f"[-] No '{filter_str}' QR codes found to print.")
            return

        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; }}
                .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; padding: 20px; }}
                .card {{ border: 1px dashed #ccc; padding: 10px; }}
                img {{ width: 100px; height: 100px; }}
                h4 {{ margin: 5px 0 0 0; font-size: 12px; }}
            </style>
        </head>
        <body onload="window.print()">
            <h2>6 SAI Strelizia Command: {title}</h2>
            <div class="grid">
        """
        
        for file in target_files:
            # Note: Using absolute paths so the browser can read local images
            img_src = os.path.abspath(os.path.join(QR_DIR, file))py
            name_label = file.replace('.png', '')
            html_content += f'<div class="card"><img src="{img_src}"><h4>{name_label}</h4></div>'

        html_content += "</div></body></html>"
        
        with open(html_path, "w") as f:
            f.write(html_content)
            
        # Open in default browser to trigger print dialog
        webbrowser.open(f"file://{os.path.abspath(html_path)}")
        self.log(f"[+] Print Spool generated. Opening web browser for hardware printing.")

class StreliziaApp(App):
    def build(self):
        Builder.load_string(KV)
        sm = ScreenManager()
        sm.add_widget(WizardScreen(name='wizard'))
        sm.add_widget(OpsScreen(name='ops'))
        sm.add_widget(CatalogScreen(name='catalog'))
        sm.add_widget(HRScreen(name='hr'))
        sm.add_widget(AnalyticsScreen(name='analytics'))
        return sm

if __name__ == "__main__":
    StreliziaApp().run()
