from __future__ import print_function

import ast

from compas.utilities import geometric_key
from compas.utilities import color_to_colordict

from compas_rhino.geometry.surface import RhinoSurface

import compas_rhino

try:
    import Rhino
    from Rhino.Geometry import Point3d
    import scriptcontext as sc
    import rhinoscriptsyntax as rs
except ImportError:
    import platform
    if platform.python_implementation() == 'IronPython':
        raise


__author__    = ['Tom Van Mele', ]
__copyright__ = 'Copyright 2016 - Block Research Group, ETH Zurich'
__license__   = 'MIT License'
__email__     = 'vanmelet@ethz.ch'


__all__ = [
    'mesh_from_guid',
    'mesh_from_surface',
    'mesh_from_surface_uv',
    'mesh_from_surface_heightfield',
    'mesh_draw',
    'mesh_draw_vertices',
    'mesh_draw_edges',
    'mesh_draw_faces',
    'mesh_select_vertices',
    'mesh_select_vertex',
    'mesh_select_edges',
    'mesh_select_edge',
    'mesh_select_faces',
    'mesh_select_face',
    'mesh_update_vertex_attributes',
    'mesh_update_edge_attributes',
    'mesh_update_face_attributes',
    'mesh_display_vertex_labels',
    'mesh_display_edge_labels',
    'mesh_display_face_labels',
    'mesh_move_vertex',
]


# ==============================================================================
# constructors
# ==============================================================================


def mesh_from_guid(cls, guid, **kwargs):
    vertices, faces = compas_rhino.get_mesh_vertices_and_faces(guid)
    faces = [face[:-1] if face[-2] == face[-1] else face for face in faces]
    mesh  = cls.from_vertices_and_faces(vertices, faces)
    mesh.attributes.update(kwargs)
    return mesh


def mesh_from_surface(cls, guid, **kwargs):
    gkey_xyz = {}
    faces = []
    obj = sc.doc.Objects.Find(guid)

    if not obj.Geometry.HasBrepForm:
        return

    brep = Rhino.Geometry.Brep.TryConvertBrep(obj.Geometry)

    for loop in brep.Loops:
        curve = loop.To3dCurve()
        segments = curve.Explode()
        face = []
        sp = segments[0].PointAtStart
        ep = segments[0].PointAtEnd
        sp_gkey = geometric_key(sp)
        ep_gkey = geometric_key(ep)
        gkey_xyz[sp_gkey] = sp
        gkey_xyz[ep_gkey] = ep
        face.append(sp_gkey)
        face.append(ep_gkey)

        for segment in segments[1:-1]:
            ep = segment.PointAtEnd
            ep_gkey = geometric_key(ep)
            face.append(ep_gkey)
            gkey_xyz[ep_gkey] = ep

        faces.append(face)

    gkey_index = {gkey: index for index, gkey in enumerate(gkey_xyz)}
    vertices = [list(xyz) for gkey, xyz in gkey_xyz.items()]
    faces = [[gkey_index[gkey] for gkey in f] for f in faces]
    mesh = cls.from_vertices_and_faces(vertices, faces)
    mesh.attributes.update(kwargs)

    return mesh


def mesh_from_surface_uv(cls, guid, density=(10, 10), **kwargs):
    return mesh_from_surface_heightfield(cls, guid, density=density, **kwargs)


def mesh_from_surface_heightfield(cls, guid, density=(10, 10), **kwargs):
    """Create a mesh data structure from a point grid aligned with the uv space of a Rhino NURBS surface.

    Parameters:
        cls (compas.datastructures.mesh.Mesh): The class of mesh that will be created.
        guid (str): The GUID of the Rhino surface.
        density (tuple): Optional. The density of the grid in the direction of u and v.
        kwargs (dict): Optional. Mesh attributes in the form of keyword arguments.

    Returns:
        compas.datastructures.mesh.Mesh: The mesh that was created.

    """
    try:
        u, v = density
    except Exception:
        u, v = density, density

    surface = RhinoSurface(guid)

    mesh = cls()
    mesh.attributes.update(kwargs)

    vertices = surface.heightfield(density=(u, v), over_space=True)

    for x, y, z in vertices:
        mesh.add_vertex(x=x, y=y, z=z)

    for i in range(u - 1):
        for j in range(v - 1):
            face = ((i + 0) * v + j,
                    (i + 0) * v + j + 1,
                    (i + 1) * v + j + 1,
                    (i + 1) * v + j)
            mesh.add_face(face)

    return mesh


# ==============================================================================
# drawing
# ==============================================================================

def mesh_draw(mesh,
              layer=None,
              clear_layer=False,
              show_faces=True,
              show_vertices=True,
              show_edges=False,
              vertexcolor=None,
              edgecolor=None,
              facecolor=None):
    """
    Draw a mesh object in Rhino.

    Parameters
    ----------
    mesh : compas.datastructures.Mesh
        The mesh object.
    layer : str (None)
        The layer to draw in.
        Default is to draw in the current layer.
    clear_layer : bool (False)
        Clear the drawing layer.
    show_faces : bool (True)
        Draw the faces.
    show_vertices : bool (True)
        Draw the vertices.
    show_edges : bool (False)
        Draw the edges.
    vertexcolor : str, tuple, list, dict (None)
        The vertex color specification.
        Default is to use the color of the parent layer.
    edgecolor : str, tuple, list, dict (None)
        The edge color specification.
        Default is to use the color of the parent layer.
    facecolor : str, tuple, list, dict (None)
        The face color specification.
        Default is to use the color of the parent layer.

    Note
    ----
    Colors can be specifiedin different ways:

    * str: A hexadecimal color that will be applied to all elements subject to the specification.
    * tuple, list: RGB color that will be applied to all elements subject to the specification.
    * dict: RGB or hex color dict with a specification for some or all of the related elements.

    Important
    ---------
    RGB colors specified as values between 0 and 255, should be integers.
    RGB colors specified as values between 0.0 and 1.0, should be floats.

    """
    guids = compas_rhino.get_objects(name='{0}.*'.format(mesh.attributes['name']))
    compas_rhino.delete_objects(guids)

    if clear_layer:
        if not layer:
            compas_rhino.clear_current_layer()
        else:
            compas_rhino.clear_layer(layer)

    if show_vertices:
        mesh_draw_vertices(mesh, color=vertexcolor, layer=layer, clear_layer=False, redraw=False)

    if show_edges:
        mesh_draw_edges(mesh, color=edgecolor, layer=layer, clear_layer=False, redraw=False)

    if show_faces:
        mesh_draw_faces(mesh, color=facecolor, layer=layer, clear_layer=False, redraw=False)

    rs.EnableRedraw()
    rs.Redraw()


def mesh_draw_vertices(mesh, keys=None, color=None, layer=None, clear_layer=False, redraw=True):
    """Draw a selection of vertices of the mesh.

    Parameters
    ----------
    mesh : compas.datastructures.Mesh
        A mesh object.
    keys : list (None)
        A list of vertex keys identifying which vertices to draw.
        Default is to draw all vertices.
    color : str, tuple, dict (None)
        The color specififcation for the vertices.
        Colors should be specified in the form of a string (hex colors) or as a tuple of RGB components.
        To apply the same color to all vertices, provide a single color specification.
        Individual colors can be assigned using a dictionary of key-color pairs.
        Missing keys will be assigned the default vertex color (``self.defaults['vertex.color']``).
        Default is use the color of the parent layer.
    layer : str (None)
        The layer in which the vertices are drawn.
        Default is to draw in the current layer.
    clear_layer : bool (False)
        Clear the drawing layer.
    redraw : bool (True)
        Redraw the view after adding the vertices.

    Notes
    -----
    The vertices are named using the following template:
    ``"{}.vertex.{}".format(self.mesh.attributes['name'], key)``.
    This name is used afterwards to identify vertices of the meshin the Rhino model.

    Examples
    --------
    >>>

    """
    guids = compas_rhino.get_objects(name='{0}.vertex.*'.format(mesh.attributes['name']))
    compas_rhino.delete_objects(guids)

    keys = keys or list(mesh.vertices())
    colordict = color_to_colordict(color, keys, default=None, colorformat='rgb', normalize=False)
    points = []
    for key in keys:
        points.append({
            'pos'  : mesh.vertex_coordinates(key),
            'name' : mesh.vertex_name(key),
            'color': colordict[key]
        })
    return compas_rhino.xdraw_points(points, layer=layer, clear=clear_layer, redraw=redraw)


def mesh_draw_edges(mesh, keys=None, color=None, layer=None, clear_layer=False, redraw=True):
    """Draw a selection of edges of the mesh.

    Parameters
    ----------
    keys : list
        A list of edge keys (as uv pairs) identifying which edges to draw.
        Default is to draw all edges.
    color : str, tuple, dict
        The color specififcation for the edges.
        Colors should be specified in the form of a string (hex colors) or as a tuple of RGB components.
        To apply the same color to all faces, provide a single color specification.
        Individual colors can be assigned using a dictionary of key-color pairs.
        Missing keys will be assigned the default face color (``self.defaults['face.color']``).
        Default is use the color of the parent layer.
    layer : str (None)
        The layer in which the edges are drawn.
        Default is to draw in the current layer.
    clear_layer : bool (False)
        Clear the drawing layer.
    redraw : bool (True)
        Redraw the view after adding the edges.

    Notes
    -----
    All edges are named using the following template:
    ``"{}.edge.{}-{}".fromat(self.mesh.attributes['name'], u, v)``.
    This name is used afterwards to identify edges of the mesh in the Rhino model.

    Examples
    --------
    >>> mesh_draw_edges(mesh)
    >>> mesh_draw_edges(mesh, color='#ff0000')
    >>> mesh_draw_edges(mesh, color=(255, 0, 0))
    >>> mesh_draw_edges(mesh, keys=mesh.edges_on_boundary())
    >>> mesh_draw_edges(mesh, color={(u, v): '#00ff00' for u, v in mesh.edges_on_boundary()})

    """
    guids = compas_rhino.get_objects(name='{0}.edge.*'.format(mesh.attributes['name']))
    compas_rhino.delete_objects(guids)

    keys = keys or list(mesh.edges())
    colordict = color_to_colordict(color, keys, default=None, colorformat='rgb', normalize=False)
    lines = []
    for u, v in keys:
        lines.append({
            'start': mesh.vertex_coordinates(u),
            'end'  : mesh.vertex_coordinates(v),
            'name' : mesh.edge_name(u, v),
            'color': colordict[(u, v)],
        })
    return compas_rhino.xdraw_lines(lines, layer=layer, clear=clear_layer, redraw=redraw)


def mesh_draw_faces(mesh, keys=None, color=None, layer=None, clear_layer=False, redraw=True, join_faces=False):
    """Draw a selection of faces of the mesh.

    Parameters
    ----------
    keys : list (None)
        A list of face keys identifying which faces to draw.
        Default is to draw all faces.
    color : str, tuple, dict (None)
        The color specififcation for the faces.
        Colors should be specified in the form of a string (hex colors) or as a tuple of RGB components.
        To apply the same color to all faces, provide a single color specification.
        Individual colors can be assigned using a dictionary of key-color pairs.
        Missing keys will be assigned the default face color (``self.defaults['face.color']``).
        Default is to use the color of the parent layer.
    layer : str (None)
        The layer in which the edges are drawn.
        Default is to draw in the current layer.
    clear_layer : bool (False)
        Clear the drawing layer.
    redraw : bool (True)
        Redraw the view after adding the edges.
    join_faces : bool (False)
        Join the faces into a polymesh object.

    Notes
    -----
    The faces are named using the following template:
    ``"{}.face.{}".format(self.mesh.attributes['name'], key)``.
    This name is used afterwards to identify faces of the mesh in the Rhino model.

    Examples
    --------
    >>>

    """
    guids = compas_rhino.get_objects(name='{0}.face.*'.format(mesh.attributes['name']))
    compas_rhino.delete_objects(guids)

    keys = keys or list(mesh.faces())
    colordict = color_to_colordict(color, keys, default=None, colorformat='rgb', normalize=False)
    faces = []
    for key in keys:
        faces.append({
            'points': mesh.face_coordinates(key),
            'name'  : mesh.face_name(key),
            'color' : colordict[key],
        })

    guids = compas_rhino.xdraw_faces(faces, layer=layer, clear=clear_layer, redraw=redraw)

    if join_faces:
        guid = rs.JoinMeshes(guids, delete_input=True)
        return guid

    return guids


# ==============================================================================
# selection
# ==============================================================================


def mesh_select_vertices(mesh, message="Select mesh vertices."):
    """Select vertices of a mesh.

    Parameters:
        mesh (compas.datastructures.mesh.Mesh): The mesh object.
        message (str): Optional. The message to display to the user.
            Default is ``"Select mesh vertices."``

    Returns:
        list: The keys of the selected vertices.

    Note:
        Selection is based on naming conventions.
        When a mesh is drawn using the function :func:`mesh_draw`,
        the point objects representing the vertices get assigned a name that
        has the following pattern::

            '{0}.vertex.{1}'.format(mesh.attributes['name'], key)

    Example:

        .. code-block:: python

            import compas
            import compas_rhino as rhino as rhino
            from compas.datastructures.mesh import Mesh

            mesh = Mesh.from_obj(compas.get_data('faces.obj'))

            keys = compas_rhino.mesh_select_vertices(mesh)

            print(keys)


    See Also:
        * :func:`mesh_select_edges`
        * :func:`mesh_select_faces`

    """
    keys = []
    guids = rs.GetObjects(message, preselect=True, filter=rs.filter.point | rs.filter.textdot)
    if guids:
        prefix = mesh.attributes['name']
        seen = set()
        for guid in guids:
            name = rs.ObjectName(guid).split('.')
            if 'vertex' in name:
                if not prefix or prefix in name:
                    key = name[-1]
                    if not seen.add(key):
                        key = ast.literal_eval(key)
                        keys.append(key)
    return keys


def mesh_select_vertex(mesh, message="Select a mesh vertex"):
    """Select one vertex of a mesh.

    Parameters:
        mesh (compas.datastructures.mesh.Mesh): The mesh object.
        message (str): Optional. The message to display to the user.
            Default is ``"Select mesh vertex."``

    Returns:
        * str: The key of the selected vertex.
        * None: If no vertex was selected.

    See Also:
        * :func:`mesh_select_vertices`

    """
    guid = rs.GetObject(message, preselect=True, filter=rs.filter.point | rs.filter.textdot)
    if guid:
        prefix = mesh.attributes['name']
        name = rs.ObjectName(guid).split('.')
        if 'vertex' in name:
            if not prefix or prefix in name:
                key = name[-1]
                key = ast.literal_eval(key)
                return key
    return None


def mesh_select_edges(mesh, message="Select mesh edges"):
    """Select edges of a mesh.

    Parameters:
        mesh (compas.datastructures.mesh.Mesh): The mesh object.
        message (str): Optional. The message to display to the user.
            Default is ``"Select mesh edges."``

    Returns:
        list: The keys of the selected edges. Each key is a *uv* pair.

    Note:
        Selection is based on naming conventions.
        When a mesh is drawn using the function :func:`mesh_draw`,
        the curve objects representing the edges get assigned a name that
        has the following pattern::

            '{0}.edge.{1}-{2}'.format(mesh.attributes['name'], u, v)

    See Also:
        * :func:`mesh_select_vertices`
        * :func:`mesh_select_faces`

    """
    keys = []
    guids = rs.GetObjects(message, preselect=True, filter=rs.filter.curve | rs.filter.textdot)
    if guids:
        prefix = mesh.attributes['name']
        seen = set()
        for guid in guids:
            name = rs.ObjectName(guid).split('.')
            if 'edge' in name:
                if not prefix or prefix in name:
                    key = name[-1]
                    if not seen.add(key):
                        u, v = key.split('-')
                        u = ast.literal_eval(u)
                        v = ast.literal_eval(v)
                        keys.append((u, v))
    return keys


def mesh_select_edge(mesh, message="Select a mesh edge"):
    """Select one edge of a mesh.

    Parameters:
        mesh (compas.datastructures.mesh.Mesh): The mesh object.
        message (str): Optional. The message to display to the user.
            Default is ``"Select mesh edges."``

    Returns:
        tuple: The key of the selected edge.
        None: If no edge was selected.

    See Also:
        * :func:`mesh_select_edges`

    """
    guid = rs.GetObject(message, preselect=True, filter=rs.filter.curve | rs.filter.textdot)
    if guid:
        prefix = mesh.attributes['name']
        name = rs.ObjectName(guid).split('.')
        if 'edge' in name:
            if not prefix or prefix in name:
                key = name[-1]
                u, v = key.split('-')
                u = ast.literal_eval(u)
                v = ast.literal_eval(v)
                return u, v
    return None


def mesh_select_faces(mesh, message='Select mesh faces.'):
    """Select faces of a mesh.

    Parameters:
        mesh (compas.datastructures.mesh.Mesh): The mesh object.
        message (str): Optional. The message to display to the user.
            Default is ``"Select mesh edges."``

    Returns:
        list: The keys of the selected faces.

    Note:
        Selection of faces is based on naming conventions.
        When a mesh is drawn using the function :func:`mesh_draw`,
        the curve objects representing the edges get assigned a name that
        has the following pattern::

            '{0}.edge.{1}-{2}'.format(mesh.attributes['name'], u, v)

    Example:

        .. code-block:: python
            :emphasize-lines: 14

            import compas
            import compas_rhino as rhino as rhino

            from compas.datastructures.mesh import Mesh

            mesh = Mesh.from_obj(compas.get_data('faces.obj'))

            find_mesh_faces(mesh, mesh.leaves())

            compas_rhino.mesh_draw(mesh)
            compas_rhino.mesh_display_face_labels(mesh)

            fkeys = compas_rhino.mesh_select_faces(mesh)

            print(fkeys)


    See Also:
        * :func:`mesh_select_vertices`
        * :func:`mesh_select_edges`

    """
    keys = []
    guids = rs.GetObjects(message, preselect=True, filter=rs.filter.textdot)
    if guids:
        prefix = mesh.attributes['name']
        seen = set()
        for guid in guids:
            name = rs.ObjectName(guid).split('.')
            if 'face' in name:
                if not prefix or prefix in name:
                    key = name[-1]
                    if not seen.add(key):
                        key = ast.literal_eval(key)
                        keys.append(key)
    return keys


def mesh_select_face(mesh, message='Select face.'):
    """Select one face of a mesh.

    Parameters:
        mesh (compas.datastructures.mesh.Mesh): The mesh object.
        message (str): Optional. The message to display to the user.
            Default is ``"Select mesh edges."``

    Returns:
        tuple: The key of the selected face.
        None: If no face was selected.

    See Also:
        * :func:`mesh_select_faces`

    """
    guid = rs.GetObjects(message, preselect=True, filter=rs.filter.textdot)
    if guid:
        prefix = mesh.attributes['name']
        name = rs.ObjectName(guid).split('.')
        if 'face' in name:
            if not prefix or prefix in name:
                key = name[-1]
                key = ast.literal_eval(key)
                return key
    return None


# ==============================================================================
# attributes
# ==============================================================================


def mesh_update_attributes(mesh):
    """Update the attributes of a mesh.

    Parameters:
        mesh (compas.datastructures.mesh.Mesh): The mesh object.

    Returns:
        bool: ``True`` if the update was successful, and ``False`` otherwise.

    Example:

        .. code-block:: python

            import compas
            import compas_rhino as rhino
            from compas.datastructures.mesh import Mesh

            mesh = Mesh.from_obj(compas.get_data('faces.obj'))

            if compas_rhino.mesh_update_attributes(mesh):
                print('mesh attributes updated')
            else:
                print('mesh attributres not updated')


    See Also:
        * :func:`mesh_update_vertex_attributes`
        * :func:`mesh_update_edge_attributes`
        * :func:`mesh_update_face_attributes`

    """
    names  = sorted(mesh.attributes.keys())
    values = [str(mesh.attributes[name]) for name in names]
    values = compas_rhino.update_named_values(names, values)
    if values:
        for name, value in zip(names, values):
            try:
                mesh.attributes[name] = ast.literal_eval(value)
            except (TypeError, ValueError):
                mesh.attributes[name] = value
        return True
    return False


def mesh_update_vertex_attributes(mesh, keys, names=None):
    """Update the attributes of the vertices of a mesh.

    Parameters:
        mesh (compas.datastructures.mesh.Mesh): The mesh object.
        keys (tuple, list): The keys of the vertices to update.
        names (tuple, list): Optional. The names of the atrtibutes to update.
            Defaults to ``None``. If ``None``, all attributes are included in the
            update.

    Returns:
        bool: ``True`` if the update was successful, and ``False`` otherwise.

    Example:

        .. code-block:: python

            import compas
            import compas_rhino as rhino

            from compas.datastructures.mesh import Mesh

            mesh = Mesh.from_obj(compas.get_data('faces.obj'))

            keys = mesh.vertices()

            if compas_rhino.mesh_update_vertex_attributes(mesh, keys):
                print('mesh vertex attributes updated')
            else:
                print('mesh vertex attributes not updated')


    See Also:
        * :func:`mesh_update_attributes`
        * :func:`mesh_update_edge_attributes`
        * :func:`mesh_update_face_attributes`

    """
    if not names:
        names = mesh.default_vertex_attributes.keys()
    names = sorted(names)
    values = [mesh.vertex[keys[0]][name] for name in names]
    if len(keys) > 1:
        for i, name in enumerate(names):
            for key in keys[1:]:
                if values[i] != mesh.vertex[key][name]:
                    values[i] = '-'
                    break
    values = map(str, values)
    values = compas_rhino.update_named_values(names, values)
    if values:
        for name, value in zip(names, values):
            if value != '-':
                for key in keys:
                    try:
                        mesh.vertex[key][name] = ast.literal_eval(value)
                    except (TypeError, ValueError):
                        mesh.vertex[key][name] = value
        return True
    return False


def mesh_update_edge_attributes(mesh, keys, names=None):
    """Update the attributes of the edges of a mesh.

    Parameters:
        mesh (compas.datastructures.mesh.Mesh): The mesh object.
        keys (tuple, list): The keys of the edges to update. Note that the keys
            should be pairs of vertex keys.
        names (tuple, list): Optional. The names of the atrtibutes to update.
            Defaults to ``None``. If ``None``, all attributes are included in the
            update.

    Returns:
        bool: ``True`` if the update was successful, and ``False`` otherwise.

    Example:

        .. code-block:: python

            import compas
            import compas_rhino as rhino

            from compas.datastructures.mesh import Mesh

            mesh = Mesh.from_obj(compas.get_data('faces.obj'))

            keys = mesh.edges()

            if compas_rhino.mesh_update_edge_attributes(mesh, keys):
                print('mesh edge attributes updated')
            else:
                print('mesh edge attributes not updated')


    See Also:
        * :func:`mesh_update_attributes`
        * :func:`mesh_update_vertex_attributes`
        * :func:`mesh_update_face_attributes`

    """
    if not names:
        names = mesh.default_edge_attributes.keys()

    names = sorted(names)

    u, v = keys[0]
    values = [mesh.edge[u][v][name] for name in names]

    if len(keys) > 1:
        for i, name in enumerate(names):
            for u, v in keys[1:]:
                if values[i] != mesh.edge[u][v][name]:
                    values[i] = '-'
                    break

    values = map(str, values)
    values = compas_rhino.update_named_values(names, values)

    if values:
        for name, value in zip(names, values):
            if value != '-':
                for u, v in keys:
                    try:
                        mesh.edge[u][v][name] = ast.literal_eval(value)
                    except (TypeError, ValueError):
                        mesh.edge[u][v][name] = value

        return True

    return False


def mesh_update_face_attributes(mesh, fkeys, names=None):
    """Update the attributes of the faces of a mesh.

    Parameters:
        mesh (compas.datastructures.mesh.Mesh): The mesh object.
        keys (tuple, list): The keys of the faces to update.
        names (tuple, list): Optional. The names of the atrtibutes to update.
            Defaults to ``None``. If ``None``, all attributes are included in the
            update.

    Returns:
        bool: ``True`` if the update was successful, and ``False`` otherwise.

    Example:

        .. code-block:: python

            import compas
            import compas_rhino as rhino

            from compas.datastructures.mesh import Mesh

            mesh = Mesh.from_obj(compas.get_data('faces.obj'))

            keys = mesh.faces()

            if compas_rhino.mesh_update_face_attributes(mesh, keys):
                print('mesh face attributes updated')
            else:
                print('mesh face attributes not updated')


    See Also:
        * :func:`mesh_update_attributes`
        * :func:`mesh_update_vertex_attributes`
        * :func:`mesh_update_edge_attributes`

    """
    if not mesh.facedata:
        return
    if not names:
        names = sorted(mesh.default_face_attributes.keys())
    values = [mesh.facedata[fkeys[0]][name] for name in names]
    if len(fkeys) > 1:
        for i, name in enumerate(names):
            for fkey in fkeys[1:]:
                if values[i] != mesh.facedata[fkey][name]:
                    values[i] = '-'
                    break
    values = map(str, values)
    values = compas_rhino.update_attributes(names, values)
    if values:
        for name, value in zip(names, values):
            if value != '-':
                for fkey in fkeys:
                    try:
                        mesh.facedata[fkey][name] = ast.literal_eval(value)
                    except (TypeError, ValueError):
                        mesh.facedata[fkey][name] = value
        return True
    return False


# ==============================================================================
# labels
# ==============================================================================


def mesh_display_vertex_labels(mesh, attr_name=None, layer=None, color=None, formatter=None):
    """Display labels for the vertices of a mesh.

    Parameters:
        mesh (compas.datastructures.mesh.Mesh): The mesh object.
        attr_name (str): Optional. The name of the attribute value to display in the label.
            Default is ``None``. If ``None``, the key of the vertex is displayed.
        layer (str): Optional. The layer to draw in. Default is ``None``.
        color (str, tuple, list, dict): Optional. The color specification. Default is ``None``.
            The following values are supported:

                * str: A HEX color. For example, ``'#ff0000'``.
                * tuple, list: RGB color. For example, ``(255, 0, 0)``.
                * dict: A dictionary of RGB and/or HEX colors.

            If ``None``, the default vertex color of the mesh will be used.
        formatter (callable): Optional. A formatting function. Default is ``None``.

    Example:

        .. code-block:: python

            import compas
            import compas_rhino as rhino

            from compas.datastructures.mesh import Mesh

            mesh = Mesh.from_obj(compas.get_data('faces.obj'))

            compas_rhino.mesh_display_vertex_labels(mesh)


        .. code-block:: python

            import compas
            import compas_rhino as rhino

            from compas.datastructures.mesh import Mesh

            mesh = Mesh.from_obj(compas.get_data('faces.obj'))

            def formatter(value):
                return '{0:.3f}'.format(value)

            compas_rhino.mesh_display_vertex_labels(mesh, attr_name='x' formatter=formatter)


    See Also:
        * :func:`mesh_display_edge_labels`
        * :func:`mesh_display_face_labels`

    """
    compas_rhino.delete_objects(compas_rhino.get_objects(name="{0}.vertex.label.*".format(mesh.attributes['name'])))

    if not attr_name:
        attr_name = 'key'

    colordict = color_to_colordict(color,
                                   mesh.vertices(),
                                   default=mesh.attributes['color.vertex'],
                                   colorformat='rgb',
                                   normalize=False)
    if formatter:
        if not callable(formatter):
            raise Exception('The provided formatter is not callable.')
    else:
        formatter = str

    labels = []

    for index, (key, attr) in enumerate(mesh.vertices(True)):
        if 'key' == attr_name:
            value = key
        elif 'index' == attr_name:
            value = index
        else:
            value = attr[attr_name]

        labels.append({'pos'  : mesh.vertex_coordinates(key),
                       'text' : formatter(value),
                       'name' : '{0}.vertex.label.{1}'.format(mesh.attributes['name'], key),
                       'color': colordict[key], })

    compas_rhino.xdraw_labels(
        labels,
        layer=layer,
        clear=False,
        redraw=True
    )


def mesh_display_edge_labels(mesh, attr_name=None, layer=None, color=None, formatter=None):
    """Display labels for the edges of a mesh.

    Parameters:
        mesh (compas.datastructures.mesh.Mesh): The mesh object.
        attr_name (str): Optional. The name of the attribute value to display in the label.
            Default is ``None``. If ``None``, the key of the edge is displayed.
        layer (str): Optional. The layer to draw in. Default is ``None``.
        color (str, tuple, list, dict): Optional. The color specification. Default is ``None``.
            The following values are supported:

                * str: A HEX color. For example, ``'#ff0000'``.
                * tuple, list: RGB color. For example, ``(255, 0, 0)``.
                * dict: A dictionary of RGB and/or HEX colors.

            If ``None``, the default edge color of the mesh will be used.
        formatter (callable): Optional. A formatting function. Default is ``None``.

    Example:

        .. code-block:: python

            import compas
            import compas_rhino as rhino

            from compas.datastructures.mesh import Mesh

            mesh = Mesh.from_obj(compas.get_data('faces.obj'))

            compas_rhino.mesh_display_edge_labels(mesh)


    See Also:
        * :func:`mesh_display_vertex_labels`
        * :func:`mesh_display_face_labels`

    """
    compas_rhino.delete_objects(compas_rhino.get_objects(name="{0}.edge.label.*".format(mesh.attributes['name'])))

    if not attr_name:
        attr_name = 'key'

    colordict = color_to_colordict(color,
                                   mesh.edges(),
                                   default=mesh.attributes['color.edge'],
                                   colorformat='rgb',
                                   normalize=False)
    if formatter:
        if not callable(formatter):
            raise Exception('The provided formatter is not callable.')
    else:
        formatter = str

    labels = []

    for index, (u, v, attr) in enumerate(mesh.edges(True)):

        if attr_name == 'key':
            value = '{0}-{1}'.format(u, v)
        elif attr_name == 'index':
            value = index
        else:
            value = attr[attr_name]

        labels.append({'pos'  : mesh.edge_midpoint(u, v),
                       'text' : formatter(value),
                       'name' : '{0}.edge.label.{1}-{2}'.format(mesh.attributes['name'], u, v),
                       'color': colordict[(u, v)], })

    compas_rhino.xdraw_labels(
        labels,
        layer=layer,
        clear=False,
        redraw=True
    )


def mesh_display_face_labels(mesh, attr_name=None, layer=None, color=None, formatter=None):
    """Display labels for the faces of a mesh.

    Parameters:
        mesh (compas.datastructures.mesh.Mesh): The mesh object.
        attr_name (str): Optional. The name of the attribute value to display in the label.
            Default is ``None``. If ``None``, the key of the face is displayed.
        layer (str): Optional. The layer to draw in. Default is ``None``.
        color (str, tuple, list, dict): Optional. The color specification. Default is ``None``.
            The following values are supported:

                * str: A HEX color. For example, ``'#ff0000'``.
                * tuple, list: RGB color. For example, ``(255, 0, 0)``.
                * dict: A dictionary of RGB and/or HEX colors.

            If ``None``, the default face color of the mesh will be used.
        formatter (callable): Optional. A formatting function. Default is ``None``.

    Example:

        .. code-block:: python

            import compas
            import compas_rhino as rhino

            from compas.datastructures.mesh import Mesh

            mesh = Mesh.from_obj(compas.get_data('faces.obj'))

            compas_rhino.mesh_display_face_labels(mesh)


    See Also:
        * :func:`mesh_display_vertex_labels`
        * :func:`mesh_display_edge_labels`

    """
    compas_rhino.delete_objects(compas_rhino.get_objects(name="{0}.face.label.*".format(mesh.attributes['name'])))

    if not attr_name:
        attr_name = 'key'

    colordict = color_to_colordict(color,
                                   mesh.faces(),
                                   default=mesh.attributes['color.face'],
                                   colorformat='rgb',
                                   normalize=False)

    if formatter:
        if not callable(formatter):
            raise Exception('The provided formatter is not callable.')
    else:
        formatter = str

    labels = []

    for index, fkey in enumerate(mesh.faces()):
        if attr_name == 'key':
            value = fkey
        elif attr_name == 'index':
            value = index
        else:
            value = mesh.facedata[fkey][attr_name]

        labels.append({
            'pos'  : mesh.face_centroid(fkey),
            'text' : formatter(value),
            'name' : '{0}.face.label.{1}'.format(mesh.attributes['name'], fkey),
            'color': colordict[fkey]
        })

    compas_rhino.xdraw_labels(
        labels,
        layer=layer,
        clear=False,
        redraw=True
    )


# ==============================================================================
# geometry
# ==============================================================================


def mesh_display_vertex_normals(mesh,
                                display=True,
                                layer=None,
                                scale=1.0,
                                color=(0, 0, 255)):

    guids = compas_rhino.get_objects(name='{0}.vertex.normal.*'.format(mesh.attributes['name']))
    compas_rhino.delete_objects(guids)

    if not display:
        return

    lines = []

    for key in mesh.vertices():
        normal = mesh.vertex_normal(key)
        start  = mesh.vertex_coordinates(key)
        end    = [start[axis] + normal[axis] for axis in range(3)]
        name   = '{0}.vertex.normal.{1}'.format(mesh.attributes['name'], key)

        lines.append({
            'start': start,
            'end'  : end,
            'name' : name,
            'color': color,
            'arrow': 'end',
        })

    compas_rhino.xdraw_lines(lines, layer=layer, clear=False, redraw=True)


def mesh_display_face_normals(mesh,
                              display=True,
                              layer=None,
                              scale=1.0,
                              color=(0, 0, 255)):

    guids = compas_rhino.get_objects(name='{0}.face.normal.*'.format(mesh.attributes['name']))
    compas_rhino.delete_objects(guids)

    if not display:
        return

    lines = []

    for fkey in mesh.faces():
        normal = mesh.face_normal(fkey)
        start  = mesh.face_center(fkey)
        end    = [start[axis] + normal[axis] for axis in range(3)]
        name   = '{0}.face.normal.{1}'.format(mesh.attributes['name'], fkey)

        lines.append({
            'start' : start,
            'end'   : end,
            'name'  : name,
            'color' : color,
            'arrow' : 'end',
        })

    compas_rhino.xdraw_lines(lines, layer=layer, clear=False, redraw=True)


# ==============================================================================
# geometry
# ==============================================================================


def mesh_move_vertex(mesh, key, constraint=None, allow_off=None, redraw=True):
    """Move on vertex of the mesh.

    Parameters:
        mesh (compas.datastructures.mesh.Network): The mesh object.
        key (str): The vertex to move.
        constraint (Rhino.Geometry): Optional. A ``Rhino.Geometry`` object to
            constrain the movement to. Default is ``None``.
        allow_off (bool): Optional. Allow the vertex to move off the constraint.
            Default is ``None``.

    Example:

        .. code-block:: python

            import compas
            import compas_rhino as rhino

            from compas.datastructures.mesh import Network

            mesh = Mesh.from_obj(compas.get_data('lines.obj'))

            key = compas_rhino.mesh_select_vertex(mesh)

            if key:
                compas_rhino.mesh_move_vertex(mesh, key)

    """
    color = Rhino.ApplicationSettings.AppearanceSettings.FeedbackColor
    nbrs  = [mesh.vertex_coordinates(nbr) for nbr in mesh.halfedge[key]]
    nbrs  = [Point3d(*xyz) for xyz in nbrs]

    def OnDynamicDraw(sender, e):
        for ep in nbrs:
            sp = e.CurrentPoint
            e.Display.DrawDottedLine(sp, ep, color)

    gp = Rhino.Input.Custom.GetPoint()
    gp.SetCommandPrompt('Point to move to?')
    gp.DynamicDraw += OnDynamicDraw

    if constraint:
        if allow_off is not None:
            gp.Constrain(constraint, allow_off)
        else:
            gp.Constrain(constraint)

    gp.Get()

    if gp.CommandResult() == Rhino.Commands.Result.Success:
        pos = list(gp.Point())
        mesh.vertex[key]['x'] = pos[0]
        mesh.vertex[key]['y'] = pos[1]
        mesh.vertex[key]['z'] = pos[2]

    if redraw:
        try:
            mesh.draw()
        except AttributeError:
            # this may result in the mesh being drawn in a different layer then before
            mesh_draw(mesh)


# ==============================================================================
# Debugging
# ==============================================================================

if __name__ == "__main__":

    pass
