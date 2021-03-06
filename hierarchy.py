from PIL import ImageFont
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.factory import Factory
from kivy.graphics import Line, Color
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.screenmanager import Screen

from schema import *


FILE_PATH = ''
FONT_SIZE = 20


def schedule(func):
    def decorate(*args):
        Clock.schedule_once(callback=lambda *_: func(*args))
    return decorate


class Hierarchy(Screen):
    def __init__(self, args, **kwargs):
        super().__init__(**kwargs)
        self._parse_args(args)
        lines = File(FILE_PATH).get_lines()
        self.struct = Struct(lines)

        self.name_button_map = dict()
        self.line_colors = list()
        self.colored_node_name = str()
        self.is_visible = True

    def on_release_back_button(self, back_button):
        [event.cancel() for event in Clock.get_events()]
        self._show_search()

    def on_release_show_button(self, show_button):
        if not self.is_visible:
            self.is_visible = True
            self._reset_line_colors()

    def on_release_hide_button(self, hide_button):
        if self.is_visible:
            self.is_visible = False
            self._reset_line_colors()

    def on_release_search_item_button(self, item_button):
        schema_name = item_button.text
        schema = self.struct.get_schema_by_name(schema_name)
        family = self.struct.get_family_by_schema(schema)

        self._show_tree()
        self._add_gridlayouts_to_tree(count=family.get_max_depth() + 1)
        self._add_buttons_to_tree(schema, family)
        self._center_layouts()
        self._add_lines_to_tree(schema)

    def on_release_tree_node(self, name):
        schema = self.struct.get_schema_by_name(name)
        description = str()

        # Type
        if schema.types:
            description += 'Types\n'
            for type in schema.types:
                description += '        ' + type + '\n'
            description += '\n\n'

        # Description
        for key, value in schema.descriptions.items():
            description += key.capitalize() + '\n'
            for item in value:
                description += '        ' + item + '\n'
            description += '\n\n'

        # Open popup
        popup = Factory.CustomPopup()
        popup.title = name
        popup.description = description
        popup.open()

    def on_text_search_input(self, text_input):
        if self._search_input_is_valid(text_input):
            search_result = self._get_schemas_by_keyword(text_input.text.lower())
            search_result.sort()
            self._set_search_result(search_result)

    def _add_gridlayouts_to_tree(self, count):
        for _ in range(count):
            gridlayout = GridLayout(rows=1, size_hint=(None, None), height=40, pos_hint={'x': 0, 'y': 0})
            gridlayout.width = gridlayout.minimum_width
            gridlayout.spacing = 10
            self.ids.tree_layout.add_widget(gridlayout)

    def _add_button_to_tree(self, level, name, center):
        layout = self.ids.tree_layout.children[level]
        short_name = name[name.find(' ') + 1: -1]
        button = Button(
            text=short_name,
            font_name='Montserrat-Medium.ttf',
            font_size=FONT_SIZE,
            color=(0,0,0,1),
            background_normal='',
            background_color=(1,1,0,1) if center else (0,0,0,0),
            size_hint=(None, 1),
            width=ImageFont.truetype(font='Montserrat-Medium.ttf', size=FONT_SIZE).getlength(text=short_name) + FONT_SIZE,
            pos_hint={'x': 0, 'y': 0},
            on_release=lambda *_: self.on_release_tree_node(name=name)
        )
        layout.add_widget(button)
        layout.width = sum([widget.width for widget in layout.children]) + (layout.spacing[0] * (len(layout.children) - 1))
        self.name_button_map[name] = button

    def _add_buttons_to_tree(self, schema, family):
        self.name_button_map = dict()
        for member in family.members:
            self._add_button_to_tree(
                level=family.get_max_depth() - member.depth,
                name=member.name,
                center=member.name == schema.name
            )

    @schedule
    @schedule
    def _add_lines_to_tree(self, schema):
        self.line_colors = list()
        self._add_line_to_parents(schema)
        self._add_line_to_children(schema)
        Window.bind(mouse_pos=self._color_lines)

    def _add_line_to_parents(self, schema):
        if schema.parents:
            my_point = self._get_center_point_by_name(schema.name)
            for parent in schema.parents:
                parent_point = self._get_center_point_by_name(parent.name)
                with self.name_button_map[schema.name].canvas:
                    color = Color(rgba=[0,0,0,1])
                    Line(points=[my_point[0], my_point[1] + FONT_SIZE, parent_point[0], parent_point[1] - FONT_SIZE], width=1)
                    self.line_colors.append(LineColor(schema.name, parent.name, color))
                self._add_line_to_parents(schema=parent)

    def _add_line_to_children(self, schema):
        if schema.children:
            my_point = self._get_center_point_by_name(schema.name)
            for child in schema.children:
                child_point = self._get_center_point_by_name(child.name)
                with self.name_button_map[schema.name].canvas:
                    color = Color(rgba=[0,0,0,1])
                    Line(points=[my_point[0], my_point[1] - FONT_SIZE, child_point[0], child_point[1] + FONT_SIZE], width=1)
                    self.line_colors.append(LineColor(schema.name, child.name, color))
                self._add_line_to_children(schema=child)

    def _button_collides(self, button, pos):
        x1, y1 = button.to_window(*button.pos)
        x2, y2 = x1 + button.width, y1 + button.height
        if pos[0] >= x1 and pos[0] <= x2 and pos[1] >= y1 and pos[1] <= y2:
            return True
        return False

    @schedule
    def _center_layouts(self):
        max_width = self.ids.tree_layout.width
        for layout in self.ids.tree_layout.children:
            left_padding = (max_width - layout.width) / 2
            layout.padding = (left_padding, 0, 0, 0)

    def _color_lines(self, window, pos):
        for name, button in self.name_button_map.items():
            if self._button_collides(button, pos):
                if name != self.colored_node_name:
                    self._reset_line_colors()
                    schema = self.struct.get_schema_by_name(name=name)
                    family_names = set(schema.get_family_names())
                    for line_color in self.line_colors:
                        if line_color.node_name_1 in family_names and line_color.node_name_2 in family_names:
                            line_color.color.rgba = [1, 0, 0, 1]
                    self.colored_node_name = name
                return
        if self.colored_node_name != str():
            self.colored_node_name = str()
            self._reset_line_colors()

    def _get_center_point_by_name(self, name):
        button = self.name_button_map[name]
        x = button.x + button.width / 2
        y = button.y + button.height / 2
        return x, y

    def _get_schemas_by_keyword(self, keyword):
        search_result = list()
        for schema in self.struct.schemas:
            if keyword in schema.name:
                search_result.append(schema.name)
        return search_result

    def _parse_args(self, args):
        global FILE_PATH, FONT_SIZE
        FILE_PATH = args.p
        FONT_SIZE = args.f if args.f else 20
        self.ids.tree_layout.spacing = args.s if args.s else 100

    def _reset_line_colors(self):
        for line_color in self.line_colors:
            line_color.color.rgba = [0, 0, 0, 1] if self.is_visible else [0, 0, 0, 0]

    def _search_input_is_valid(self, text_input):
        text = text_input.text.lower()
        if not text:
            self.ids.search_result.clear_widgets()
            return False
        if text == ' ' or text[-1] == '\t':
            text_input.text = text[:-1]
            return False
        return True

    def _set_search_result(self, search_result: list):
        self.ids.search_result.clear_widgets()
        for item in search_result:
            button = Button(
                text=item,
                color=(0, 0, 0, 1),
                font_size=FONT_SIZE,
                background_normal='',
                background_color=(0, 0, 0, 0),
                size_hint=(1, None),
                height=100,
                pos_hint={'x': 0, 'y': 0},
                on_release=lambda *bound_args: self.on_release_search_item_button(bound_args[0])
            )
            self.ids.search_result.add_widget(button)

    def _show_search(self):
        self.ids.tree.pos_hint = {'x': 1, 'y': 0}
        self.ids.search.pos_hint = {'x': 0, 'y': 0}
        self.ids.tree_layout.clear_widgets()

    def _show_tree(self):
        self.ids.search.pos_hint = {'x': 1, 'y': 0}
        self.ids.tree.pos_hint = {'x': 0.01, 'top': 0.99}
        self.ids.search_input.text = ''
        self.ids.search_result.clear_widgets()

    def _sort_family_by_height(self, family):
        sorted_family = list()
        for member in family:
            if not sorted_family:
                sorted_family.append(member)
            else:
                for i in range(len(sorted_family)):
                    if member.height >= sorted_family[i].height:
                        sorted_family.insert(i, member)
                        break
                if member not in sorted_family:
                    sorted_family.append(member)
        return sorted_family


class LineColor:
    def __init__(self, name1, name2, color):
        self.node_name_1 = name1
        self.node_name_2 = name2
        self.color = color