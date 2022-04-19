#### Monkey patch qtpynodeeditor to allow for multiple input connections
# Patch aims to allow multiple inputs to a node, not implemented yet

import qtpynodeeditor
from qtpynodeeditor import exceptions
import uuid
from qtpynodeeditor.connection_geometry import ConnectionGeometry

from qtpynodeeditor import (PortType, Connection)


def new_init(self, port_a, port_b=None, *, style, converter=None):
    super(Connection, self).__init__()
    self._uid = str(uuid.uuid4())

    if port_a is None:
        raise ValueError('port_a is required')
    elif port_a is port_b:
        raise ValueError('Cannot connect a port to itself')

    if port_a.port_type == PortType.input:
        in_port = port_a
        out_port = port_b
    else:
        in_port = port_b
        out_port = port_a

    if in_port is not None and out_port is not None:
        if in_port.port_type == out_port.port_type:
            raise exceptions.PortsOfSameTypeError(
                'Cannot connect two ports of the same type')

    self._ports = {PortType.input: in_port, PortType.output: out_port}

    if in_port is not None:
        if in_port.connections:
            conn, = in_port.connections
            existing_in, existing_out = conn.ports
            if existing_in == in_port and existing_out == out_port:
                raise exceptions.PortsAlreadyConnectedError(
                    'Specified ports already connected')
            raise exceptions.MultipleInputConnectionError(
                f'Maximum one connection per input port '
                f'(existing: {conn})')

    if in_port and out_port:
        self._required_port = PortType.none
    elif in_port:
        self._required_port = PortType.output
    else:
        self._required_port = PortType.input

    self._last_hovered_node = None
    self._converter = converter
    self._style = style
    self._connection_geometry = ConnectionGeometry(style)
    self._graphics_object = None


qtpynodeeditor.Connection.__init__ = new_init

### End Patch

#### Monkey Patch connection drawing
# Patches wrong type, orig: QPoint, correct: QPointF

from qtpy.QtCore import QSize, Qt, QPointF
from qtpy.QtGui import QIcon, QPen

from qtpynodeeditor.connection_geometry import ConnectionGeometry
from qtpynodeeditor.enums import PortType
import qtpynodeeditor.connection_painter


def draw_normal_line(painter, connection, style):
    if connection.requires_port:
        return

    # colors
    normal_color_out = style.get_normal_color()
    normal_color_in = normal_color_out

    selected_color = style.selected_color

    gradient_color = False
    if style.use_data_defined_colors:
        data_type_out = connection.data_type(PortType.output)
        data_type_in = connection.data_type(PortType.input)

        gradient_color = data_type_out.id != data_type_in.id

        normal_color_out = style.get_normal_color(data_type_out.id)
        normal_color_in = style.get_normal_color(data_type_in.id)
        selected_color = normal_color_out.darker(200)

    # geometry
    geom = connection.geometry
    line_width = style.line_width

    # draw normal line
    p = QPen()
    p.setWidth(line_width)

    graphics_object = connection.graphics_object
    selected = graphics_object.isSelected()

    cubic = qtpynodeeditor.connection_painter.cubic_path(geom)
    if gradient_color:
        painter.setBrush(Qt.NoBrush)

        c = normal_color_out
        if selected:
            c = c.darker(200)

        p.setColor(c)
        painter.setPen(p)

        segments = 60

        for i in range(segments):
            ratio_prev = float(i) / segments
            ratio = float(i + 1) / segments

            if i == segments / 2:
                c = normal_color_in
                if selected:
                    c = c.darker(200)

                p.setColor(c)
                painter.setPen(p)

            painter.drawLine(cubic.pointAtPercent(ratio_prev),
                             cubic.pointAtPercent(ratio))

        icon = QIcon(":convert.png")

        pixmap = icon.pixmap(QSize(22, 22))
        painter.drawPixmap(
            cubic.pointAtPercent(0.50) - QPointF(pixmap.width() / 2,
                                                 pixmap.height() / 2), pixmap)
    else:
        p.setColor(normal_color_out)

        if selected:
            p.setColor(selected_color)

        painter.setPen(p)
        painter.setBrush(Qt.NoBrush)

        painter.drawPath(cubic)


qtpynodeeditor.connection_painter.draw_normal_line = draw_normal_line

### End patch

#### Monkey Patch auto layouts
# Patches more options for auto layouts

import qtpynodeeditor.flow_scene


def auto_arrange(self,
                 layout='planar_layout',
                 scale=700,
                 align='horizontal',
                 **kwargs):
    '''
    Automatically arrange nodes with networkx, if available
    Raises
    ------
    ImportError
        If networkx is unavailable
    '''
    import networkx
    dig = self.to_digraph()
    print(dig)

    try:
        if hasattr(networkx.layout, layout):
            layout_func = getattr(networkx.layout, layout)
        else:
            layout_func = getattr(networkx.nx_agraph, layout)
    except KeyError:
        raise ValueError('Unknown layout type {}'.format(layout)) from None

    layout = layout_func(dig, **kwargs)
    for node, pos in layout.items():
        pos_x, pos_y = pos
        node.position = (pos_x * scale, pos_y * scale)


qtpynodeeditor.flow_scene.FlowScene.auto_arrange = auto_arrange
### End patch

# #### Monkey Patch to allow attatching to click on node graphic
# import qtpynodeeditor.node_graphics_object

# prev_mouseMoveEvent_fn = qtpynodeeditor.node_graphics_object.NodeGraphicsObject.mousePressEvent
