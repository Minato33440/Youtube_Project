exec((__import__('pathlib').Path(__file__).parent/'review.py').read_text().split('hashes=')[0])
P=ROOT/'art/eye_adjust_v007/parts'
def bg(im,color=(80,105,110)):
 c=Image.new('RGBA',im.size,color+(255,));c.alpha_composite(im);return c.convert('RGB')
mapping={0:'face_underfill',1:'FILL_eye_white_R',2:'ALT_iris_R_brown',3:'lower_eyelid_right',4:'ALT_eyelash_upper_R',5:'FILL_eye_white_L',6:'ALT_iris_L_blue',7:'lower_eyelid_left',8:'ALT_eyelash_upper_L',9:'mouth_closed',10:'brow_L',11:'brow_R'}
checks=[]
for idx,n in mapping.items():
 a=Image.open(OUT/f'layer_{idx:02d}.png').convert('RGBA');b=Image.open(P/(n+'.png')).convert('RGBA');b=b.crop(b.getbbox());a=a.crop(a.getbbox());variants=[]
 for flip in [False,True]:
  z=b.transpose(Image.Transpose.FLIP_LEFT_RIGHT) if flip else b
  z=z.resize(a.size,Image.Resampling.LANCZOS)
  err=float(np.abs(np.array(bg(a)).astype(float)-np.array(bg(z)).astype(float)).mean())
  variants.append({'flip':flip,'mean_abs_error':err})
 checks.append({'layer':idx,'name':n,'psd_size':a.size,'source_size':b.size,'variants':variants})
print(json.dumps(checks,indent=2))
(OUT/'psd_source_check.json').write_text(json.dumps(checks,indent=2),encoding='utf8')
for side in ['L','R']:
 im=Image.open(ROOT/f'art/processing_v001/front/parts/iris_{side}_original.png')
 print('Original iris',side,im.size,im.convert('RGBA').getbbox())
print('lower_lids_identical',np.array_equal(np.array(Image.open(P/'lower_eyelid_left.png')),np.array(Image.open(P/'lower_eyelid_right.png'))))
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
sample=Image.open(P/'facial features.png').convert('RGBA')
sheet=Image.new('RGB',(1200,840),(65,65,65));d=ImageDraw.Draw(sheet)
crops=[('A. Lower rim - brown eye',(192,650,354,712)),('B. Lower rim - blue eye',(488,650,658,714)),('C. Face contour - cheek',(627,696,704,821)),('D. Face contour - chin',(352,945,498,1008))]
for i,(label,box) in enumerate(crops):
 x=(i%2)*600;y=(i//2)*420;im=bg(sample.crop(box)).resize(((box[2]-box[0])*3,(box[3]-box[1])*3),Image.Resampling.NEAREST)
 sheet.paste(im,(x+15,y+45));d.text((x+15,y+10),label,font=font,fill='white')
sheet.save(OUT/'edge_details.jpg',quality=98)
