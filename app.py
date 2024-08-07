from nicegui import ui
import bot, asyncio
import config
import pandas as pd
from sqlalchemy import create_engine
from threading import Thread
from static import *
from io import BytesIO
import psycopg2

ui.add_head_html(
    """  
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    """
)

class Home:
    def __init__(self) -> None:
        self.address = None
        self.state = None
        self.house = None
        self.street = None
        self.city = None
        self.county = None
        self.zip = None
        self.payload = {}
        self.search_metadata = {"info": "Please run query 1 before you can see last query info"}
        self.property_ids = []
        self.original_property_ids = []
        self.eng = create_engine(config.db_url)
        self.page_num = 0
        self.remove_all = None
        self.output_df = pd.DataFrame()
        self.dfs = []
    
    #Long running tasks-----------------
    async def query2_runner(self):
        try:
            if self.remove_all == 'Remove all':
                q = f"SELECT p_id FROM {config.db_name} WHERE p_id IN {tuple(self.original_property_ids)}"
                df_gen = self.query_data_from_df(q, ['p_id'])
                dup_list = df_gen['p_id'].to_list()
                self.property_ids = [p for p in self.property_ids if p not in dup_list]
                self.output_df = await bot.get_property_details(self.property_ids)
            elif self.remove_all == 'Update all':
                self.output_df = await bot.get_property_details(self.original_property_ids)
            else:
                self.output_df = await bot.get_property_details(self.property_ids)
            if len(self.output_df) > 0:
                self.download_btn.enable()
            else:
                with self.page_col:
                    ui.notification(
                    "No data extracted", close_button=True, timeout=10, position='top')
        except Exception as e:
            with self.page_col:
                ui.notification(
                    f""" Error: {e}""",
                    position='top',
                    multi_line=True,
                    close_button=True, timeout=10, type='negative'
                )
        finally:
            self.spinner.visible = False
        
    def before_query2(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        loop.run_until_complete(self.query2_runner())
        loop.close()
        
    #Backend----------------------------
    
    def query_data_from_df(self, query: str, cols: list):
        with psycopg2.connect(config.con_string) as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                df_gen = pd.DataFrame(cur.fetchall(), columns=cols)
        return df_gen

    def add_or_not(self, value, p_id, df: pd.DataFrame):
        try:
            if value:
                self.property_ids.remove(p_id)
            else:
                self.property_ids.append(p_id)
            df.loc[df['p_id'] == p_id, 'checked'] = value
        except ValueError:
            pass

    async def start_query2(self):
        self.spinner.visible = True
        task = Thread(target=self.before_query2)
        task.start()
            
    def filter_based_on_db(self):
        q = None
        with self.eng.connect() as con:
            if len(self.property_ids) > 1:
                q = f'''SELECT p_id, first_name, last_name, 
                address, property_type, pre_foreclosure, vacant, owner_occupied
                FROM {config.db_name} WHERE p_id IN {tuple(self.property_ids)}'''
            elif len(self.property_ids) == 1:
                q = f'''SELECT p_id, first_name, last_name, 
                address, property_type, pre_foreclosure, vacant, owner_occupied
                FROM {config.db_name} WHERE p_id = {self.property_ids[0]}'''
            if q:
                df_gen = pd.read_sql_query(q, con, chunksize=5)
                self.dfs = list(df_gen)
                if not self.dfs[0].empty:
                    self.total_data = len(self.dfs)
                    self.show_data(self.dfs[self.page_num])
                else:
                    with self.duplicate_ui:
                        self.total_data = 1
                        ui.label("""
                        No duplicates found, you can proceed with query 2.
                        You can use the (SHOW LAST QUERY BUTTON) to view inspect the query info""")\
                        .classes('w-full text-pretty text-center')
                        self.show_duplicate_buttons()
            else:
                with self.page_col:
                    ui.notification("No property for this query", type='info', close_button=True)
                
    def change_page(self):
        try:
            df = self.dfs[self.page_num]
            self.show_data(df)
        except IndexError:
            self.show_data(pd.DataFrame())
        
    def runner(self):
        print(self.payload)
        try:
            self.property_ids, self.search_metadata, error = bot.get_property_id(self.payload)
            if not error:
                #self.property_ids = [33951715, 25638409, 44804953]
                self.property_ids = [str(p) for p in self.property_ids]
                self.original_property_ids = self.property_ids.copy()
                self.loc_ui.value = False
                self.prop_ui.value = False
                self.query2_ui.visible = True
                self.filter_based_on_db()
            else:
                self.search_metadata = self.payload.copy()
                with self.page_col:
                    ui.notification(f"Error while running the query: {error}", 
                    multi_line=True, position='top', timeout=10, close_button=True)
        except Exception as e:
            self.search_metadata = self.payload.copy()
            with self.page_col:
                ui.notification(
                    f""" Error: {e}""",
                    position='top', timeout=10,
                    close_button=True, type='negative'
                )
        finally:
            self.spinner.visible = False
    
    def select_handler(self, value: bool, name: str):
        name = name.replace(' ', '_').lower()
        self.payload[name] = value
        if value:
            match value:
                case 'True':
                    self.payload[name] = True
                case 'False':
                    self.payload[name] = False
                case 'None':
                    self.payload[name] = None
        else:
            del self.payload[name]
    
    def toggle_handler(self, value: str):
        if value:
            self.payload['property_type'] = value
    
    def input_handler(self, value: float|str|None, name: str):
        name = f"{name.replace(' ', '_').lower()}"
        if name == 'zip':
            value: list[str] = value.split(',')
            value = [v.strip() for v in value if not (v.isspace() or (v == ''))]
        else:
            value = int(value) if type(value) == float else value
        self.payload[name] = value
        if value:
            self.payload[name] = value
        else:
            del self.payload[name]
            
    def start_query1(self):
        self.spinner.visible = True
        self.duplicate_ui.clear()
        self.payload['count'] = True
        self.payload['summary'] = True
        self.payload['ids_only'] = True
        task = Thread(target=self.runner)
        task.start()
                   
    def handle_download(self):
        buffer = BytesIO()
        writer = pd.ExcelWriter(buffer, engine='openpyxl')
        self.output_df.to_excel(writer, index=False)
        writer.close()
        ui.download(
            buffer.getvalue(),
            'output.xlsx',
            'application/vnd.ms-excel'
        )
        
    #Frontend-----------------------------
    
    def property_toggler(self):
        with ui.column(align_items='center')\
            .classes(f'w-full p-3 border-4 overflow-auto max-h-80 max-2xl:hidden col-span-2'):
                ui.toggle(property_types, clearable=True).on_value_change(
                    lambda e: self.toggle_handler(e.value)
                ).classes('flex flex-col w-full justify-center')
                
        with ui.column(align_items='start').classes('w-full p-3 border-4 2xl:hidden'):
            with ui.expansion("PROPERTY TYPES").classes('w-full bg-accent').props('header-class="text-bold"'):
                ui.toggle(property_types, clearable=True).on_value_change(
                    lambda e: self.toggle_handler(e.value)
                ).classes('flex flex-col w-full justify-center')
    
    def small_screen_show_data(self, row):
        for col in to_show_cols[:2]:
            with ui.item().classes('col-span-2 w-full lg:hidden items-stretch'):
                with ui.item_section():
                    ui.item_label(col['name']).classes('text-bold')
                    ui.item_label(row[col['field']]).props('caption').classes('text-bold')
    
    def large_screen_show_data(self, row):
        for col in to_show_cols:
            with ui.item().classes('col-span-1 w-full max-lg:hidden items-stretch'):
                with ui.item_section():
                    ui.item_label(col['name']).classes('text-bold')
                    ui.item_label(row[col['field']]).props('caption').classes('text-bold')

    def show_duplicate_buttons(self):
        with self.duplicate_ui:
            with ui.column().classes('w-full justify-center pt-5'):
                ui.pagination(0, self.total_data - 1, direction_links=True)\
                .bind_value(self, 'page_num').on_value_change(
                    self.change_page
                ).classes('w-full justify-center')\
                .props(':max-pages="6" boundary-numbers')
            with ui.row().classes('w-full justify-center p-5'):
                ui.toggle(["Remove all", "Update all"], clearable=True).bind_value(
                    self, 'remove_all'
                ).props('unelevated')
                with ui.button_group().props('flat'):
                    self.start_quering = ui.button("Start query 2").on_click(
                        self.start_query2
                    )
                    self.download_btn = ui.button("Download result").on_click(
                        self.handle_download
                    )
                    self.download_btn.disable()
    
    def show_data(self, df: pd.DataFrame):
        if not 'checked' in df.columns:
            df['checked'] = False
        self.duplicate_ui.clear()
        with self.duplicate_ui:
            ui.label(duplicate_message).classes('p-2 text-pretty text-center')
            for idx, row in df.iterrows():
                with ui.row()\
                    .classes('w-full grid lg:grid-cols-8 divide-y grid-cols-5'):
                    with ui.element('div').classes('col-start-1'):
                        ui.checkbox("select", value=row['checked'])\
                            .classes('w-full justify-center').on_value_change(
                            lambda e, p_id=row['p_id']: self.add_or_not(e.value, p_id, df)
                        )
                    self.large_screen_show_data(row)
                    self.small_screen_show_data(row)
            self.show_duplicate_buttons()
                
    def query_dialog(self):
        self.q_dialog.clear()
        with self.q_dialog, ui.card():
            ui.json_editor({'content': {'json': self.search_metadata}})\
            .run_editor_method('updateProps', {'readOnly': True})
        self.q_dialog.open()
    
    def update_date_ui(self):
        with ui.column().classes('grid grid-cols-2 w-full'):
            ui.input("Min").props('stack-label outlined type="date"')\
            .on_value_change(lambda e: 
            self.input_handler(e.value, 'last_update_date_min'))
            
            ui.input("Max").props('stack-label outlined type="date"')\
            .on_value_change(lambda e: 
            self.input_handler(e.value, 'last_update_date_max'))
    
    def other_filters_ui(self):
        #large screen
        with ui.column().classes('w-full p-3 border-4 overflow-auto max-h-80 col-span-2 max-2xl:hidden'):
            ui.label("Last Update Date").classes('w-full text-bold')
            self.update_date_ui()                
            ui.label("Search Range").classes('w-full text-bold')
            ui.select(search_range_options, value='1_YEAR', clearable=True).classes('w-full')\
            .props('stack-label outlined').on_value_change(
                lambda e: self.input_handler(e.value, 'search_range')
            )
            ui.label("APN").classes('w-full text-bold')
            ui.input().classes('w-full')\
            .props('stack-label outlined').on_value_change(
                lambda e: self.input_handler(e.value, 'apn')
            )
        #small screen
        with ui.element('div').classes('2xl:hidden'):
            with ui.column().classes('w-full p-3 border-4'):
                with ui.expansion('Last Update Date').classes('w-full bg-accent').props('header-class="text-bold"'):
                    self.update_date_ui()
            with ui.column().classes('w-full p-3 border-4'):
                with ui.expansion('Search Range').classes('w-full bg-accent').props('header-class="text-bold"'):                
                    ui.select(search_range_options, value='1_YEAR', clearable=True).classes('w-full')\
                    .props('stack-label outlined').on_value_change(
                        lambda e: self.input_handler(e.value, 'search_range')
                    )
            with ui.column().classes('w-full p-3 border-4'):
                with ui.expansion('APN').classes('w-full bg-accent').props('header-class="text-bold"'):
                    ui.input().classes('w-full')\
                    .props('stack-label outlined').on_value_change(
                        lambda e: self.input_handler(e.value, 'apn')
                    )
            
    def min_max_ui(self):
        #large screen
        with ui.column().classes('w-full p-3 border-4 overflow-auto max-h-80 col-span-2 max-2xl:hidden'):
            for min_max in min_max_inputs:
                min_max = min_max.replace('_', ' ').title()
                ui.label(min_max).classes('text-bold')
                with ui.element('div').classes('grid grid-cols-2 w-full space-x-2'):
                    ui.number("min", min=1, max=2147483647).props('stack-label outlined')\
                    .on_value_change(
                        lambda e, name=min_max: self.input_handler(e.value, f'{name}_min')
                    )
                    ui.number("max", min=1, max=2147483647).props('stack-label outlined')\
                    .on_value_change(
                        lambda e, name=min_max: self.input_handler(e.value, f'{name}_max')
                    )
        #small screen         
        with ui.element('div').classes('2xl:hidden space-y-1'):
            for min_max in min_max_inputs:
                min_max = min_max.replace('_', ' ').title()
                with ui.expansion(min_max)\
                .classes('w-full p-3 border-4 flex-col').props('header-class="text-bold"'):
                    with ui.element('div').classes('grid grid-cols-2 w-full space-x-2'):
                        ui.number("min", min=1, max=2147483647).props('stack-label outlined')\
                        .on_value_change(
                            lambda e, name=min_max: self.input_handler(e.value, f'{name}_min')
                        )
                        ui.number("max", min=1, max=2147483647).props('stack-label outlined')\
                        .on_value_change(
                            lambda e, name=min_max: self.input_handler(e.value, f'{name}_max')
                        )
    
    def select_box_ui(self, name: str, values: list[str], col_span: int = 1):
        #large screen
        with ui.column(align_items='start')\
            .classes(f'w-full p-3 border-4 overflow-auto max-h-80 max-2xl:hidden col-span-{col_span}'):
            ui.label(name).classes('flex text-bold')
            for val in values:
                val = val.replace('_', ' ').title() if not val.isupper() else val.replace('_', ' ')
                ui.select(label=val, options=[
                    "True", "False", "None"
                ], clearable=True).classes('w-full').props('stack-label outlined').on_value_change(
                    lambda e, name=val: self.select_handler(e.value, name)
                )
        #small screen
        with ui.column(align_items='start').classes('w-full p-3 border-4 2xl:hidden'):
            with ui.expansion(name).classes('w-full bg-accent').props('header-class="text-bold"'):
                with ui.row().classes('w-full'):
                    for val in values:
                        val = val.replace('_', ' ').title() if not val.isupper() else val.replace('_', ' ')
                        ui.select(label=val, options=[
                            "True", "False", "None"
                        ], clearable=True).classes('w-full').props('stack-label outlined').on_value_change(
                            lambda e, name=val: self.select_handler(e.value, name)
                        )
        
    def location_ui(self):
        with self.page_col:
            with ui.expansion("Location Parameters", value=True)\
                .props('header-class="bg-primary text-black text-bold text-base md:text-xl"') as self.loc_ui:
                with ui.row().classes('grid grid-cols-2 lg:grid-cols-4 space-x-2 w-full'):
                    for lf in location_filters:
                        ui.input(label=lf['name'])\
                            .props(f'''outlined hint="{lf.get('hint')}"''').on_value_change(
                                lambda e, lf=lf: self.input_handler(e.value, lf['field'])
                            )
                    
    def property_ui(self):
        with self.page_col:
            with ui.expansion("Property Parameters", value=True)\
                .props('header-class="bg-primary text-black text-bold text-base md:text-xl"') as self.prop_ui:
                with ui.row()\
                .classes('grid grid-cols-10 max-2xl:grid-cols-1 gap-1 w-full') as self.pp_col:
                    #self.select_box_ui('PROPERTY TYPES', property_types, 2)
                    self.property_toggler()
                    self.select_box_ui("MLS", mls_statuses, 2)
                    self.select_box_ui("Other Filters", filters_part_1, 2)
                    self.min_max_ui()
                    self.other_filters_ui()

    def header(self):
        ui.query('body').style(
            'background-color: #EEEEEE;'
        )
        with ui.header().classes('bg-secondary md:justify-center'):
            ui.label("Query Builder").classes('md:text-5xl text-3xl')
            self.spinner = ui.spinner(size='40px')
            self.spinner.visible = False
                        
    def page_body(self):
        with ui.element('div').classes('grid md:grid-cols-10 w-full'):
            self.page_col = ui.element('div')\
            .classes('md:col-span-8 md:col-start-2 border-2 space-y-4')
    
    def engine(self):
        self.header()
        self.q_dialog = ui.dialog()
        self.page_body()
        self.location_ui()
        self.property_ui()
        with ui.row().classes('w-full justify-center'):
            ui.button("Start Query 1").props('unelevated')\
                .on_click(self.start_query1)
            ui.button("Show Last Query Info").props('unelevated')\
                .on_click(self.query_dialog)
        
        self.query2_ui = ui.element('div').classes('p-5 border-double border-4 border-black w-full')
        with self.query2_ui:
            ui.label("QUERY 2").classes('font-mono text-h5 justify-center w-full flex')
            self.duplicate_ui = ui.element('div').classes('w-full')
        self.query2_ui.visible = False


@ui.page('/')    
def main():
    ui.colors(
        secondary='#393E46', primary='#929AAB', accent='#EEEEEE'
    )
    home = Home()
    home.engine()  

        
ui.run(port=3333, endpoint_documentation='internal', title='Query Builder', favicon='🛠️')
    
    