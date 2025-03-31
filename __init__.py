import bpy
import os
import uuid
import time


class AddonPrefs(bpy.types.AddonPreferences):
    bl_idname = __package__ 

    AutoRefreshPreview: bpy.props.BoolProperty(
        name="Auto Refresh Previews",
        description="Refreshing Previews after operation, because after adding multiple assets previews may be missing",
        default=True, )

    def draw(self, context):
        self.layout.prop(self, "AutoRefreshPreview")   



class CreateAssetCatalog(bpy.types.Operator):
    bl_idname = "asset.create_collection_catalogs"
    bl_label = "Create Asset Catalogs"
    bl_description = "Create asset catalogs from selected collections and mark objects as assets"

    def execute(self, context):
        selected_ids = bpy.context.selected_ids
        collections = [item for item in selected_ids if hasattr(item, "id_type") and item.id_type == "COLLECTION"]
        
        if not collections:
            self.report({"WARNING"}, "No collections selected.")
            return {"CANCELLED"}
        
        global existing_catalogs
        existing_catalogs = read_existing_catalogs()
        
        for coll in collections:
            hierarchy_name = sanitize_name(coll.name)
            catalog_uuid = create_catalog(hierarchy_name, existing_catalogs)
            if catalog_uuid:
                mark_collection_objects_as_assets(coll, catalog_uuid, hierarchy_name)
        
        for area in bpy.context.screen.areas:
            if area.ui_type == 'ASSETS':
                with bpy.context.temp_override(area=area):
                    bpy.ops.asset.library_refresh()

        self.report({"INFO"}, "Asset catalogs created.") 
        return {"FINISHED"}




class GeneratePreviews(bpy.types.Operator):
    bl_idname = "asset.generate_multiple_preview"
    bl_label = "Generate Previews"
    bl_description = "Generate previews for selected objects"

    def execute(self, context):
        selected = bpy.context.selected_assets
        if selected:
            for obj in selected:
                obj_id = obj.local_id
                if obj_id:
                    try:
                        with bpy.context.temp_override(id=obj_id):
                            time.sleep(0.0001)
                            bpy.ops.ed.lib_id_generate_preview()
                    except:
                        pass
        else:
            self.report({"WARNING"}, "No objects selected.")

        self.report({"INFO"}, "Previews generated.")
        return {"FINISHED"}
    



class ClearPreviews(bpy.types.Operator):
    bl_idname = "asset.clear_multiple_preview"
    bl_label = "Clear Previews"
    bl_description = "Clear previews for selected objects"
    
    def execute(self, context):
        selected = bpy.context.selected_assets
        if selected:
            for obj in selected:
                obj_id = obj.local_id
                if obj_id:
                    try:
                        with bpy.context.temp_override(id=obj_id):
                            bpy.ops.ed.lib_id_remove_preview()
                    except:
                        pass
        else: 
            self.report({"WARNING"}, "No objects selected.")

        self.report({"INFO"}, "Previews cleared.")
        return {"FINISHED"}



def sanitize_name(name):
    return name.replace("/", "_").replace("\\", "_").replace(":", "_")



def get_catalog_path():
    blend_file_path = bpy.data.filepath

    if blend_file_path:
        project_dir = os.path.dirname(blend_file_path)
        catalog_path = os.path.join(project_dir, "blender_assets.cats.txt")
    else:
        catalog_path = None  # Unsaved blend file
    return catalog_path



def read_existing_catalogs():
    catalog_path = get_catalog_path()
    existing_catalogs = {}

    if catalog_path and os.path.exists(catalog_path):
        with open(catalog_path, "r") as file:
            for line in file:
                line = line.strip() 

                if not line or line.startswith('#'):
                    continue
                parts = line.split(":", 1)

                if len(parts) == 2:
                    catalog_uuid, catalog_name = parts
                    sanitized_catalog_name = sanitize_name(catalog_name)
                    existing_catalogs[sanitized_catalog_name] = catalog_uuid
    return existing_catalogs



def create_catalog(catalog_full_name, existing_catalogs):
    if catalog_full_name in existing_catalogs:
        return existing_catalogs[catalog_full_name]
    
    catalog_uuid = str(uuid.uuid4())
    catalog_line = f"{catalog_uuid}:{catalog_full_name}\n"
    catalog_path = get_catalog_path()

    if not catalog_path:
        print("Cant find Asset Library Path. Make Sure .blend file is saved and blender_assets.cats.txt exists right before the .blend file.")
        return None
    
    try:
        with open(catalog_path, "a") as file:
            file.write(catalog_line)
        existing_catalogs[catalog_full_name] = catalog_uuid
        return catalog_uuid
    except Exception as error:
        print(f"Error creating catalog: {error}")
        return None



def mark_collection_objects_as_assets(collection, catalog_uuid, base_path):
    for obj in collection.objects:
        if not obj.asset_data:
            obj.asset_mark()
            if bpy.context.preferences.addons[__package__].preferences.AutoRefreshPreview:
                with bpy.context.temp_override(id=obj):
                    try: 
                        time.sleep(0.0001)  # Workaround for preview generation
                        bpy.ops.ed.lib_id_generate_preview()
                    except:
                        pass
        if obj.asset_data:
            obj.asset_data.catalog_id = catalog_uuid

    for child in collection.children:
        child_base_path = f"{base_path}/{sanitize_name(child.name)}"
        child_catalog_uuid = create_catalog(child_base_path, existing_catalogs)
        if child_catalog_uuid:
            mark_collection_objects_as_assets(child, child_catalog_uuid, child_base_path)



def outliner_menu(self, context):
    self.layout.separator()
    self.layout.operator(CreateAssetCatalog.bl_idname)

def asset_menu(self, context):
    self.layout.separator()
    self.layout.operator(GeneratePreviews.bl_idname)
    self.layout.operator(ClearPreviews.bl_idname)

def register():
    bpy.utils.register_class(CreateAssetCatalog)
    bpy.utils.register_class(GeneratePreviews)
    bpy.utils.register_class(ClearPreviews)
    bpy.utils.register_class(AddonPrefs)

    bpy.types.OUTLINER_MT_collection.append(outliner_menu)
    bpy.types.ASSETBROWSER_MT_context_menu.append(asset_menu)

def unregister():
    bpy.utils.unregister_class(CreateAssetCatalog)
    bpy.utils.unregister_class(GeneratePreviews)
    bpy.utils.unregister_class(ClearPreviews)
    bpy.utils.unregister_class(AddonPrefs)

    bpy.types.OUTLINER_MT_collection.remove(outliner_menu)
    bpy.types.ASSETBROWSER_MT_context_menu.remove(asset_menu)

if __name__ == "__main__":
    register()