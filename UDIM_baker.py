bl_info = {
	"name": "UDIM Baker",
	"author": "Alfonso Annarumma & Asger Suhr Langhoff",
	"version": (0, 1, 1),
	"blender": (3, 3, 0),
	"location": "Properties > Render Properties > Bake",
	"description": "Baking UDIM Tiles with one click",
	"warning": "",
	"wiki_url": "",
	"category": "Render",
}


import bpy
import os
import bmesh


def create_udim_dictionary(obj):
	"""[creates a dictionary of the UDIM tiles
	that have vertices in them]

	Args:
		obj ([blender mesh object]): [current mesh object]

	Returns:
		[dictionary]: [contains all the uv vectors, for each UDIM]
	"""
	me = obj.data
	bm = bmesh.new()
	bm = bmesh.from_edit_mesh(me)
	tiles = {}
	uv_layer = bm.loops.layers.uv.verify()

	for f in bm.faces:
		 for l in f.loops:
			 column = int(l[uv_layer].uv[0])
			 row = int(l[uv_layer].uv[1])
			 udim_nr = 1001 + column + (row * 10)
			 if udim_nr in tiles:
				 tiles[udim_nr] = (column, row)
			 else:
				 tiles[udim_nr] = ()
				 tiles[udim_nr] = (column, row)
	return tiles


def uv_translate(tiles, obj, udim):
	"""[Moves the current udim to UDIM 1001 position,
	the only UDIM that blender bakes]

	Args:
		tiles ([tuple]): [should contain the original row and column of the current UDIM]
		obj ([blender mesh object]): [current mesh object]
		udim ([integer]): [UDIM number]
	"""
	me = obj.data
	bm = bmesh.new()
	bm = bmesh.from_edit_mesh(me)
	uv_layer = bm.loops.layers.uv.verify()
	for f in bm.faces:
		for l in f.loops:
			l[uv_layer].uv[0] = l[uv_layer].uv[0] - tiles[udim][0]
			l[uv_layer].uv[1] = l[uv_layer].uv[1] - tiles[udim][1]

	me.update()


def uv_restore(tiles, obj, udim):
	"""[Moves the current udim back to its original position]

	Args:
		tiles ([tuple]): [should contain the original row and column of the current UDIM]
		obj ([blender mesh object]): [current mesh object]
		udim ([integer]): [UDIM number]
	"""

	me = obj.data
	bm = bmesh.new()
	bm = bmesh.from_edit_mesh(me)
	uv_layer = bm.loops.layers.uv.verify()
	for f in bm.faces:
		for l in f.loops:
			l[uv_layer].uv[0] = l[uv_layer].uv[0] + tiles[udim][0]
			l[uv_layer].uv[1] = l[uv_layer].uv[1] + tiles[udim][1]

	me.update()


def bake_udim(context):
	obj = bpy.context.view_layer.objects.active

	data = bpy.data
	images = data.images
	mat = obj.active_material
	nodes = mat.node_tree.nodes
	if nodes.active.type == 'TEX_IMAGE':
		if nodes.active.image.source =='TILED':

			udim_node = nodes.active
			udim = udim_node.image
			basename = bpy.path.basename(udim.filepath)
			udim_name = basename.split('.')[0]
			udim_dir = os.path.dirname(bpy.path.abspath(udim.filepath))
			split = udim.filepath.split('.')
			ext = split[-1]


			list = []

			for t in udim.tiles:
				list.append(t.number)

			i = 0

			if obj.mode != 'EDIT':
				bpy.ops.object.editmode_toggle()
			tiles = create_udim_dictionary(obj)
			if obj.mode == 'EDIT':
				bpy.ops.object.editmode_toggle()
			for n in list:
				if n in tiles.keys():

					if obj.mode != 'EDIT':
						bpy.ops.object.editmode_toggle()

						uv_translate(tiles, obj, n)

					if obj.mode == 'EDIT':
						bpy.ops.object.editmode_toggle()
					bake = images.new("bake", udim.size[0], udim.size[1], alpha=True, float_buffer=udim.is_float, stereo3d=False, is_data=False, tiled=False)
					bake_node = nodes.new("ShaderNodeTexImage")
					bake_node.name = "bake_image"
					bake_node.image = bake
					nodes.active = bake_node
					bake_node.select = True


					filepath = udim_dir+'/'+udim_name+'.'+str(n)+"."+ext
					filepath = filepath.replace("<","")
					filepath = filepath.replace(">","")
					print(filepath)
					bake.filepath = filepath
					bake.save_render(filepath=filepath)

					bake.source = 'FILE'

					check_multires = bpy.context.scene.render.use_bake_multires
					type = bpy.context.scene.cycles.bake_type

					if check_multires:
						bpy.ops.object.bake_image()
					else:
						bpy.ops.object.bake(type = type, filepath=filepath, save_mode='EXTERNAL')

					bake.save()

					nodes.remove(bake_node)
					images.remove(bake)

					if obj.mode != 'EDIT':
						bpy.ops.object.editmode_toggle()

						uv_restore(tiles, obj, n)

					if obj.mode == 'EDIT':
						bpy.ops.object.editmode_toggle()
					i += 1



			nodes.active = udim_node
			udim.reload()
		else:
			print("Select Udim Node")
	else:
		print("Select Udim Node")


class SCENE_OT_Bake_Udim(bpy.types.Operator):
	"""Select a UDIM Image Node"""
	bl_idname = "object.bake_udim"
	bl_label = "Bake to UDIM tiles"

	@classmethod
	def poll(cls, context):
		return context.active_object is not None

	def execute(self, context):

		bake_udim(bpy.context)

		return {'FINISHED'}


def menu_func(self, context):

	layout = self.layout
	layout.operator("object.bake_udim")


def register():
	bpy.utils.register_class(SCENE_OT_Bake_Udim)
	bpy.types.CYCLES_RENDER_PT_bake.append(menu_func)


def unregister():
	bpy.utils.unregister_class(SCENE_OT_Bake_Udim)
	bpy.types.CYCLES_RENDER_PT_bake.remove(menu_func)

if __name__ == "__main__":
	register()
