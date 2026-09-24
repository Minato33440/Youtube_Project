exec((__import__('pathlib').Path(__file__).parent/'review.py').read_text())
# Draft cut runs inside the collar material; nothing is removed from the original.
poly=[(1850,1256),(2155,1256),(2140,1320),(2100,1400),(2050,1480),(1995,1550),(1940,1480),(1890,1400),(1860,1320)]
shirt=images['shirt_torso'].copy();sx,sy=pos['shirt_torso'];local=[(x-sx,y-sy) for x,y in poly]
mask=Image.new('L',shirt.size);ImageDraw.Draw(mask).polygon(local,fill=255)
mask.save(OUT/'shirt_cut_mask_DRAFT.png')
a=np.array(shirt);a[:,:,3][np.array(mask)>0]=0;trial=Image.fromarray(a)
images['shirt_torso']=trial;save(assemble(),'collar_cut_trial',(1600,980,2400,1720));images['shirt_torso']=shirt
guide=bg(assemble().crop((1600,980,2400,1720)));d=ImageDraw.Draw(guide)
p=[(x-1600,y-980) for x,y in poly];d.line(p+[p[0]],fill=(255,40,80),width=3)
for i,(x,y) in enumerate(p):d.ellipse((x-4,y-4,x+4,y+4),fill='yellow');d.text((x+7,y-20),str(i+1),font=font,fill=(255,50,70))
guide.save(OUT/'shirt_cut_guide.jpg',quality=96)
shirtguide=bg(shirt);d=ImageDraw.Draw(shirtguide);d.line(local+[local[0]],fill=(255,40,80),width=3)
for i,(x,y) in enumerate(local):d.text((x+7,max(0,y-22)),str(i+1),font=font,fill=(200,0,40))
shirtguide.save(OUT/'shirt_cut_local.jpg',quality=96)
(OUT/'shirt_cut_coordinates.json').write_text(json.dumps({'status':'unapplied draft; approximate, follow collar interior and retain underlap','shirt_size':shirt.size,'shirt_global_origin':[sx,sy],'polygon_global':poly,'polygon_shirt_local':local,'overlap_target_px':'approximately 10-20 under collar; do not cut along outside collar tips'},indent=2),encoding='utf8')
blinkdir=ROOT/'art/blink_assembly_v001/open';bm=json.loads((blinkdir/'manifest.json').read_text())
def eyes(new=False):
 c=Image.new('RGBA',(760,960));c.alpha_composite(images['face_underfill'],(77,33))
 for q in bm['layers']:
  if not q['visible'] or q['name']=='face_underfill':continue
  im=Image.open(blinkdir/q['path']).convert('RGBA');xy=(q['left'],q['top'])
  if new and q['name'].startswith('upper_lash_'):
   side=q['name'][-1];im=images['eyelash_upper_'+side+'_original'];b=im.getbbox();xy=(q['left']-b[0],q['top']-b[1])
  c.alpha_composite(im,xy)
 return c
comparison=Image.new('RGB',(1280,350),(80,105,110))
for i,new in enumerate([False,True]):
 tile=bg(eyes(new).crop((80,425,720,730)));comparison.paste(tile,(640*i,45));ImageDraw.Draw(comparison).text((640*i+15,10),'Approved ALT baseline' if not new else 'Repaired original lashes / draft placement',font=font,fill='white')
comparison.save(OUT/'eyelash_comparison.jpg',quality=97)
# Before/after at the same global crop; no rescaling of parts.
comparison=Image.new('RGB',(1440,780),(80,105,110))
for i,n in enumerate(['hair_previous','hair_current']):
 im=Image.open(OUT/(n+'.jpg'));im.thumbnail((720,730));comparison.paste(im,(i*720,45));ImageDraw.Draw(comparison).text((i*720+15,10),'Before' if i==0 else 'After / registered',font=font,fill='white')
comparison.save(OUT/'hair_comparison.jpg',quality=96)
