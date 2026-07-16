import pyvista as pv
import pyvistaqt as pvqt
import os

#Generazione finestra pyvista
def openpyvista( selected_files ):

   pv.global_theme.color_cycler = 'default'
   pv.global_theme.title = 'PLOT VIEWER'
   plotter = pv.Plotter()

   text = plotter.add_text( "Pick a geometry ...", position='upper_left', name="TEXT_TOP_LEFT" )

   #Aggiornamento della stringa posta in algo con nome elemento selezionato
   def update_text( actor ):
       text.set_text( 2,  "Filename: " + os.path.basename( actor.name ) )

   #Aggiornamento della trasparenza
   def update_opacity( value ):
     if isinstance( plotter.picked_actor, pv.Actor ):
        plotter.picked_actor.prop.opacity = value
        plotter.update()
        return

     for a in plotter.renderer.actors.values():
       if isinstance(a, pv.Actor):
           a.prop.opacity = value
     plotter.update()

   #Aggiornamento del wireframe
   def surface_wireframe( value ):
     if isinstance( plotter.picked_actor, pv.Actor ):
        plotter.picked_actor.prop.show_edges = value
        plotter.update()
        return

     for a in plotter.renderer.actors.values():
       if isinstance(a, pv.Actor):
           a.prop.show_edges = value
     plotter.update()

   #Aggiornamento della visibilità
   def visibility( value ):
     if isinstance( plotter.picked_actor, pv.Actor ):
        plotter.picked_actor.visibility = value
        plotter.update()
        return

     for a in plotter.renderer.actors.values():
       if isinstance(a, pv.Actor):
           a.visibility = value
     plotter.update()

   #Apertura di tutti i files
   for file in selected_files:
      plotter.add_mesh( pv.read( file), name=file )

   #plotter.enable_element_picking( mode='mesh', left_clicking=True, show_message=False )
   plotter.enable_mesh_picking( update_text,  left_clicking=True, show_message=False, style='surface', use_actor=True  )

   plotter.add_slider_widget( update_opacity, value=1, rng=[0, 1], title="Opacity", pointa=(0.6,0.08), pointb=(0.95,0.08), style='modern' )

   plotter.add_checkbox_button_widget( visibility, value=True, position=( 10, 10) )
   plotter.add_text( "Toggle visibility", position=( 80, 10 ) )

   plotter.add_checkbox_button_widget( surface_wireframe, value=False, position=(10, 60) )
   plotter.add_text( "Toggle wireframe", position=( 80, 60 ) )

   plotter.show_grid()

   #Comando per definizione punto
   #print( plotter.pick_click_position() )

   plotter.show()
   #plotter.show( auto_close=True, interactive_update=True )
 
   #TODO Controlli per finestra piu interattiva: da valutare
   #class PlotterControls:
   #    def __init__(self, plotter):
   #        self.plotter = plotter
   #        self.plotter.add_key_event("q", self.quit)
   #        self.stop = False
  # 
  #     def quit(self):
  #         print("Stopping")
  #         self.stop = True
  # 
  # pc = PlotterControls(plotter)
  # plotter.show( auto_close=False, interactive_update=True )
#
#      while True:  # As long as simulation is active
#          # Perform one time step of the simulation environment
#          # Update all actors to reflect the changes, e.g.
#          # Rerender:
#          print( "ADDING" )
#          plotter.add_mesh( pv.read("inlet.stl") )
#          plotter.update()  # Non-blocking call to render updated environment, this also catches the key events
#          plotter.show( auto_close=True, interactive_update=False)  # Blocking call, this also catches the key events

          #if pc.stop:
          #    plotter.close()
          #    break


      #warped = mesh.warp_by_scalar('Elevation')
      #surf = warped.extract_surface().triangulate()
      #surf = surf.decimate_pro(0.75)  # reduce the density of the mesh by 75%
      #surf.plot(cmap='gist_earth')
