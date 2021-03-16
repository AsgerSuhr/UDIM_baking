bl_info = {
    "name": "UDIM Baker",
    "author": "Alfonso Annarumma & Asger Suhr Langhoff",
    "version": (1, 2),
    "blender": (2, 80, 0),
    "location": "Properties > Render Properties > Bake",
    "description": "Baking UDIM Tiles with one click. \
	You can check the baking progress if you have the console window open.",
    "warning": "",
    "wiki_url": "https://github.com/AsgerSuhr/UDIM_baking",
    "category": "Render",
}


import bpy
from bpy.types import Operator, Object, Context
import os
import bmesh
from typing import Dict, Tuple
import sys, time

def update_progress(progress):
    barLength = 10 # Modify this to change the length of the progress bar
    status = ""
    if isinstance(progress, int):
        progress = float(progress)
    if not isinstance(progress, float):
        progress = 0
        status = "error: progress var must be float\r\n"
    if progress < 0:
        progress = 0
        status = "Halt...\r\n"
    if progress >= 1:
        progress = 1
        status = "Done...\r\n"
    block = int(round(barLength*progress))
    text = "\rPercent: [{0}] {1}% {2}".format( "#"*block + "-"*(barLength-block), progress*100, status)
    sys.stdout.write(text)
    sys.stdout.flush()

def create_udim_dictionary(obj:Object) -> Dict[int,Tuple[int, int]]:
    """
    creates a dictionary of the UDIM tiles
    that have vertices in them, 
    because if they have vertices in them they are valid.
    it returns the column and row because it's important to move the uv's
    back to their original space.

    Returns:
        [dictionary]: [UDIM number, uv vector (column, row)]
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


def uv_translate(tiles:Tuple[int,int], obj:Object, udim:int) -> None:
    """
    Moves the current UDIM tile to UDIM 1001 position,
    the only UDIM tile that blender bakes to.
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
    


def uv_restore(tiles:Tuple[int,int], obj:Object, udim:int) -> None:
    """Moves the current udim back to its original position"""
    
    me = obj.data
    bm = bmesh.new()
    bm = bmesh.from_edit_mesh(me)
    uv_layer = bm.loops.layers.uv.verify()
    for f in bm.faces:
        for l in f.loops:
            l[uv_layer].uv[0] = l[uv_layer].uv[0] + tiles[udim][0]
            l[uv_layer].uv[1] = l[uv_layer].uv[1] + tiles[udim][1]

    me.update()
    

def bake_udim(context:Context) -> None:
    """Main loop for baking to UDIM tiles"""

    # acessing necesarry data and storing it in easy to read variables
    obj = context.scene.view_layers[0].objects.active
    data = bpy.data
    images = data.images
    mat = obj.active_material
    nodes = mat.node_tree.nodes

    # checks whether the active texture node is image texture node and that it's UDIM tiled
    if nodes.active.type == 'TEX_IMAGE':
        if nodes.active.image.source =='TILED':
            
            # storing udim node and the image
            udim_node = nodes.active
            udim = udim_node.image

            # storing the path to the image file
            basename = bpy.path.basename(udim.filepath) 
            
            # getting the udim image name: udimImage.1001.png -> udimImage
            udim_name = basename.split('.')[0] 

            # getting the directory storing the images
            udim_dir = os.path.dirname(bpy.path.abspath(udim.filepath))

            # getting the extension
            split = udim.filepath.split('.') 
            ext = split[-1] 
            
            # getting a list with all the udim tiles numbers
            list = []
            for t in udim.tiles:
                list.append(t.number)

            # creates a dictionary with udim tiles
            if obj.mode != 'EDIT':
                bpy.ops.object.editmode_toggle()            
            tiles = create_udim_dictionary(obj)
            if obj.mode == 'EDIT':
                bpy.ops.object.editmode_toggle()

            wm = context.window_manager
            wm.progress_begin(0, len(tiles))
            i = 0
            for n in list:
                if n in tiles.keys():

                    # moves the current UV's to tile 1001, the only tile that blender bakes to
                    if obj.mode != 'EDIT':
                        bpy.ops.object.editmode_toggle()                    
                        uv_translate(tiles, obj, n)                    
                    if obj.mode == 'EDIT':
                        bpy.ops.object.editmode_toggle()
                    
                    # creates a new image to bake to
                    bake = images.new("bake", udim.size[0], udim.size[1], alpha=True, float_buffer=udim.is_float, stereo3d=False, is_data=False, tiled=False)

                    # copies the colorspace and alpha mode from the original image
                    bake.colorspace_settings.name = udim.colorspace_settings.name
                    bake.alpha_mode = udim.alpha_mode

                    # creates a new texture image node that we can tell blender to bake to
                    bake_node = nodes.new("ShaderNodeTexImage")
                    bake_node.name = "bake_image"

                    # assigns our new image to this node
                    bake_node.image = bake

                    # set it to be the active and selected node
                    nodes.active = bake_node
                    bake_node.select = True
                    
                    # make our filepath to save the new image to 
                    filepath = udim_dir+'/'+udim_name+'.'+str(n)+"."+ext
                    print(filepath + '\n')
                    bake.filepath = filepath
                    
                    bake.source = 'FILE'
                    
                    # checks if multiresolution baking is on or not
                    check_multires = bpy.data.scenes['Scene'].render.use_bake_multires
                    type = bpy.context.scene.cycles.bake_type
                    
                    # bakes image
                    if check_multires:
                        bpy.ops.object.bake_image()
                    else:
                        bpy.ops.object.bake(type = type, filepath=filepath, save_mode='EXTERNAL')
                    
                    # saves image
                    bake.save()
                    
                    # celanup
                    nodes.remove(bake_node)
                    images.remove(bake)
                    
                    # puts the current UV's back to it's original tile
                    if obj.mode != 'EDIT':
                        bpy.ops.object.editmode_toggle()
                    
                        uv_restore(tiles, obj, n)
                    
                    if obj.mode == 'EDIT':
                        bpy.ops.object.editmode_toggle()
                    i += 1
                    wm.progress_update(i)
                    update_progress(i/len(list))
                    
                
            wm.progress_end()
            nodes.active = udim_node
            udim.reload()
        else:
            print("Select Udim Node")
    else:
        print("Select Udim Node")
        
        
class SCENE_OT_Bake_Udim(Operator):
    """Select a UDIM Image Node"""
    bl_idname = "object.bake_udim"
    bl_label = "Bake to UDIM tiles"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):

        bake_udim(context)
        
        return {'FINISHED'}

def menu_func(self, context):
    """Adds the addon operator to the layout"""
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


