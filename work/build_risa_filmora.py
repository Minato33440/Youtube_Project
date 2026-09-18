"""Build a separate Filmora project using the existing local project's schema.

This creates an intermediate graph, not a Filmora-validated deliverable.
The minimal WFP was rejected by Filmora 15.6.4. Use prepare_filmora_trial.py
to preserve the native container metadata, then native Save As and reopen.
"""
import base64, copy, csv, hashlib, json, struct, subprocess, time, uuid, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'Politics_Economics/2026-09-09_fiscal_policy'
MEDIA=P/'media/sample_v1_risa'
def uid(): return str(uuid.uuid4())
def guid():
    parts=uid().split('-')
    return '{'+'-'.join(s.lower() if i==2 else s.upper() for i,s in enumerate(parts))+'}'
def ud(key,data):
    if isinstance(data,int): data=struct.pack('<i',data)
    elif isinstance(data,str): data=data.encode()
    return dict(key=key,data=base64.b64encode(data).decode(),size=len(data))
def dumps(v): return json.dumps(v,ensure_ascii=False,separators=(',',':'))
def normal_speed(duration):
    # Omission produces a zero-length source-time map in Filmora, freezing video.
    curve=dict(Version=3,ParameterType=0,keyframeSets=[
        dict(_time=0.0,Interpolation=6,_value=1.0),
        dict(_time=duration,Interpolation=6,_value=1.0)],_totalTime=duration)
    return dict(offset=0.0,offsetEnd=duration,reverse=False,speedParam=dumps(curve))
def main():
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--prototype',action='store_true');args=ap.parse_args()
    z=zipfile.ZipFile(P/'filmora/fiscal_policy_narration_v2.wfp')
    info=json.loads(z.read('ProjectFolder/project_info.json'))
    oldtl=info['timeline_mediaId']; tlid=guid()
    doc=json.loads(z.read(f'ProjectFolder/Medias/{oldtl}/timeline.wesproj'))
    timeline=doc['timelineInfos'][0]; original_tracks=timeline['trackInfos']
    vt=next(t for t in original_tracks if t['trackType']==1 and t['clipList'])
    at=next(t for t in original_tracks if t['trackType']==2 and t['clipList'])
    vclip=vt['clipList'][0]; aclip=at['clipList'][0]
    template=doc['resources'][0]
    media_template=json.loads(z.read('ProjectFolder/Medias/{3DE85306-B937-487a-B21A-13656535283F}/media.json'))
    rows=list(csv.DictReader((P/'code_edit/sample_v1/timeline.csv').open(encoding='utf-8-sig')))
    if args.prototype: rows=rows[:6]
    duration=round(float(rows[-1]['timeline_out'])*1e7)
    bus=uid();timeline['audioBusInfos']=[dict(balance=.5,busUid=bus,gain=0.)]
    timeline['sampleRate']=48000
    # Audio/video pairs follow the native Filmora schema; later video pairs overlay earlier ones.
    tracks=[]
    for index in range(3):
        tag=index*2+1
        tracks.append(dict(busUuids=[bus],clipList=[],trackTag=tag,trackType=2,userData=[ud(20,tag+1)],uuid=uid()))
        tracks.append(dict(clipList=[],trackTag=tag+1,trackType=1,userData=[ud(21,1),ud(12000,70)],uuid=uid()))
    timeline['trackInfos']=[dict(busUuids=[bus],clipList=[],trackType=2,uuid=uid()),*tracks]
    resources=[];media_items={};media_files={};clipmap={}; references=[]
    def add(path,row,video_track=None,audio_track=None,alpha=False):
        probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]))
        count=int(row['planned_frames']); dur=count/30; ticks=round(dur*1e7)
        begin=round(float(row['timeline_in'])*1e7); end=round(float(row['timeline_out'])*1e7)
        sourceuid=uid();mediaid=guid();clipid=guid()
        r=copy.deepcopy(template);r.update(filename='file:/'+path.as_posix(),sourceUuid=sourceuid,mediaLength=ticks,createDate=int(time.time()),modifyDate=int(time.time()))
        vs=next((s for s in probe['streams'] if s['codec_type']=='video'),None)
        au=next((s for s in probe['streams'] if s['codec_type']=='audio'),None)
        r['videoStreamCount']=int(vs is not None);r['audioStreamCount']=int(au is not None)
        r['bitRate']=int(probe['format'].get('bit_rate',0));r['alphaPremultiply']=0
        if vs:
            v=r['vidStreamInfo'][0];v.update(vidStreamId=vs['index'],width=vs['width'],height=vs['height'],xRatio=vs['width'],yRatio=vs['height'],streamLength=ticks,totalFrames=count,alphaChannel=int(alpha),bitRate=int(vs.get('bit_rate',0)),frameRate=dict(num=30,den=1))
            if alpha: v.update(fourCC=int.from_bytes(b'ap4h','little'),bitsDepth=32)
        else: r['vidStreamInfo']=[];r['streamType']=3;r['fourCC']=7758199
        if au:
            a=r['audStreamInfo'][0];a.update(audStreamId=au['index'],sampleRate=int(au['sample_rate']),channels=au['channels'],streamLength=ticks,duration=dur,bitRate=int(au.get('bit_rate',0)))
            if au['codec_name']=='pcm_s16le': a.update(fourCC=541934416,description='Uncompressed PCM',bytesPerSecond=int(au['sample_rate'])*au['channels']*2,bitDepth=16)
        else: r['audStreamInfo']=[]
        resources.append(r)
        label=path.stem+('_Live2D' if alpha else '_narration' if not vs else '_background' if path.parent.name=='backgrounds' else '')
        item=dict(download_url=path.as_posix(),id=mediaid,media_type=8 if vs else 4,media_length=ticks,name=label,mediaCreationInfo='{"creationType":0}',import_time=int(time.time()),src_md5=hashlib.md5(path.as_posix().encode()).hexdigest(),stream_idx=0,mark_info_list=[dict(mark_in=-1,mark_out=-1)],scence_info=[])
        media_items[mediaid]=item
        m=copy.deepcopy(media_template);m['file_name']=path.as_posix()
        m['sourceInfo']['basicInfo']={k:r[k] for k in ('streamType','fourCC','mediaLength','programCount','videoStreamCount','audioStreamCount','subPicStreamCount','bitRate','createDate')}
        m['sourceInfo']['vidStreamInfos']=r['vidStreamInfo'];m['sourceInfo']['audStreamInfos']=r['audStreamInfo']
        media_files[f'ProjectFolder/Medias/{mediaid}/media.json']=dumps(m)
        clipmap[clipid]=dict(mediaId=mediaid,subClips={})
        for track,typ,tem in ((video_track,1,vclip),(audio_track,2,aclip)):
            if track is None: continue
            c=copy.deepcopy(tem)
            c.update(filename=r['filename'],sourceUuid=sourceuid,thisUId=uid(),tlBegin=begin,tlEnd=end,inPoint=0,outPoint=ticks,streamId=vs['index'] if typ==1 else au['index'])
            if typ==1: c['speed']=normal_speed(dur)
            else: c.pop('speed',None)
            # Native default transform/volume; alpha asset includes placement in its full HD canvas.
            for chain in c['effectChainList']:
                for effect in chain['effectList']: effect['thisUId']=uid()
            c['userData']=[ud(102,0),ud(103,2 if typ==1 else 4),ud(1,typ),ud(2,0),ud(10,mediaid),ud(3,clipid),ud(6,timeline['timelineId']),ud(50,label)]
            timeline['trackInfos'][track]['clipList'].append(c)
        references.append(dict(path=str(path),begin_frame=round(begin/1e7*30),frames=count,media_id=mediaid))
    for row in rows:
        n=row['id']
        if row['type']=='video': add(MEDIA/'video'/f'{n}.mp4',row,2,1)
        else:
            add(MEDIA/'backgrounds'/f'{n}.mp4',row,4)
            add(MEDIA/'audio'/f'{n}.wav',row,audio_track=0)
            add(MEDIA/'live2d'/f'{n}.mov',row,6,alpha=True)
    doc['resources']=resources
    title='Risa_layered_prototype' if args.prototype else 'Sample-MP4_v1-Risa-layered'
    out=P/'filmora'/f'{title}.wfp'
    info.update(project_file_name=title,project_timeline_duration=duration,project_current_position=700,project_sample_rate=48000,timeline_mediaId=tlid,project_guid=guid(),proj_zip_save_path=out.as_posix(),project_date_create=int(time.time()),project_date_modify=int(time.time()))
    media_items[tlid]=dict(name=title,download_url='',id=tlid,timeline_uuid=guid(),media_type=1048576,create_time=int(time.time()),duration=duration,enable_modify_mediaId=0,mark_info_list=[dict(mark_in=-1,mark_out=-1)])
    # Preserve duplicate media_item keys used by Filmora's own serializer.
    folder='{"visible":"true","SerializeDataOnlyProjectUsered":"false",'+','.join('"media_item":'+dumps(k) for k in media_items if k!=tlid)+'}'
    mi='{"media_structure":{"visible":"true","SerializeDataOnlyProjectUsered":"false","Folder":'+folder+',"media_item":'+dumps(tlid)+'},"media_items":'+dumps(media_items)+'}'
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_STORED) as dest:
        for entry in z.namelist():
            if '/Anon/' in entry: dest.writestr(entry,z.read(entry))
        dest.writestr('ProjectFolder/project_info.json',dumps(info))
        dest.writestr('ProjectFolder/Medias/medias_info.json',mi)
        dest.writestr(f'ProjectFolder/Medias/{tlid}/timeline.wesproj',dumps(doc))
        dest.writestr(f'ProjectFolder/Medias/{tlid}/extra.json',dumps(dict(fontNameInfo=[],usedBizFont=[],usedTemplateResInfo={},mediaClipsMapInfo=clipmap,allMarkersInfo={},pendingMarkersInfo={},highlightInfo={},TextSentence=dict(TextSentence=[]))))
        for name,data in media_files.items(): dest.writestr(name,data)
    report=P/'code_edit/sample_v1_risa';report.mkdir(exist_ok=True)
    (report/f'{title}_structure.json').write_text(json.dumps(dict(project=str(out),duration_ticks=duration,track_clip_counts=[len(t['clipList']) for t in timeline['trackInfos']],references=references,gui_validation='pending'),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(out)
if __name__=='__main__': main()
