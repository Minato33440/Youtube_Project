"""Record provenance while retaining strict raster-regression exceptions."""
from pathlib import Path
from datetime import datetime
import hashlib, json

root = Path(__file__).resolve().parent
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
snapshot = read(root / 'input_snapshot.json')
guide = read(root / 'dense_contour_check/dense_visible_contour_target.json')
preservation = read(root / 'preservation_report.json')
contour = read(root / 'dense_contour_check/dense_contour_before_after_measurement.json')
poses = read(root / 'dense_contour_check/refined_pose_checks.json')
psd = read(root / 'dense_contour_check/dense_contour_reference_psd_readback.json')
checks = {
    'baseline_cmo3_unchanged': sha(Path(snapshot['baseline_model'])) == snapshot['baseline_sha256'],
    'rejected_cmo3_unchanged': sha(Path(snapshot['rejected_model'])) == snapshot['rejected_sha256'],
    'reference_art_unchanged': sha(Path(guide['source']['path'])) == guide['source']['sha256'],
    'saved_candidate_matches_regression': sha(root / 'Ren_face_endpoint.cmo3') == preservation['model_sha256'],
    'full_moc_matches_regression_and_pose_samples': sha(root / 'runtime/Ren_face_endpoint.moc3') == preservation['moc_sha256'] == poses['provenance']['full']['moc3_sha256'],
    'face_moc_matches_contour_and_pose_samples': sha(root / 'face_runtime/Ren_face_endpoint.moc3') == contour['models']['after_moc3_sha256'] == poses['provenance']['face']['moc3_sha256'],
    'texture_atlas_unchanged': sha(root / 'runtime/Ren_face_endpoint.2048/texture_00.png') == sha(root / 'baseline_runtime/Ren_front.2048/texture_00.png'),
    'pre_refinement_backup_unchanged': sha(root / 'archive/before_mesh_refinement_20260926/Ren_face_endpoint.cmo3') == '0869f8d9ab135174cc5f2af59d5fef188aa30e7cbdeb5a8ebadefafedb7dbe28',
    'reference_psd_readback': psd['status'] == 'pass' and sha(Path(psd['psd'])) == psd['sha256'],
    'edited_endpoint_body_unchanged': preservation['edited_endpoint']['body_below_y600_max'] == 0,
    'actual_drawable_count_preserved': len(preservation['before_drawables']) == len(preservation['after_drawables']) == 48 and poses['face_drawables'] == ['face_underfill'],
    'visible_contour_median_and_max_improved': all(contour['overall_distance']['after']['full_canvas_px'][key] < contour['overall_distance']['before']['full_canvas_px'][key] for key in ('p50', 'max')),
}
artifacts = [root / name for name in ['Ren_face_endpoint.cmo3', 'runtime/Ren_face_endpoint.moc3', 'face_runtime/Ren_face_endpoint.moc3',
    'dense_contour_check/cheek_jaw_comparison_ja.png', 'dense_contour_check/dense_contour_before_after_4up.png',
    'dense_contour_check/face_intermediate_poses_ja.png', 'dense_contour_check/face_jaw_opening_ja.png',
    'dense_contour_check/front_mouth_preservation_ja.png', 'dense_contour_check/other_pose_remesh_differences_ja.png',
    'dense_contour_check/dense_contour_reference_4000x6000.psd']]
report = {
    'checked_at': datetime.now().astimezone().isoformat(),
    'scope': 'Face-underfill remesh at X=-30/Y=-30. Eyes, mouth, ears and hair endpoint placement remains on hold.',
    'status': 'samples_ready_with_disclosed_raster_differences',
    'checks': checks,
    'artifact_and_source_checks_pass': all(checks.values()),
    'strict_18_case_display_regression_pass': preservation['all_unedited_display_cases_pass'],
    'strict_regression_note': 'False retained: remeshing changes rasterization and nonlinear parent-deformer interpolation. Do not report all prior states as pixel-identical.',
    'front_face_boundary_max_distance_render_px': poses['front_face_max_boundary_distance_render_px'],
    'front_boundary_render_size': poses['render_size'],
    'face_pose_cases_checked': len(poses['face_pose_cases']),
    'all_face_rasters_single_silhouette_alpha16': poses['all_face_rasters_single_filled_silhouette'],
    'all_face_rasters_single_silhouette_alpha64': poses['all_face_rasters_single_filled_silhouette_alpha64'],
    'low_alpha_fringe_note': 'At alpha>=16, up to 3 endpoint rows have tiny detached edge pixels at cheek/chin. None at alpha>=64 in the 32 tested states. Residual edge roughness remains.',
    'contour_distance_full_canvas_px': {key: value['full_canvas_px'] for key, value in contour['overall_distance'].items()},
    'ui_observation': 'Saved in Cubism 5.3.04 FREE at X=0/Y=0, real parts visible, reference folders hidden. Face-only and full SDK5.0 runtimes exported; export settings saved. This revision was not closed/reopened.',
    'geometry_limit': poses['geometry_limit'],
    'artistic_status': 'awaiting_Boss_contour_review_before_next_parts',
    'remaining': ['Review cheek/chin contour and residual translucent fringe', 'Keep eye/hair/ear/mouth alignment on hold until contour acceptance', 'Opposite endpoint and physics/full-assembly acceptance are outside this revision'],
    'artifacts': {str(p.relative_to(root)): {'bytes': p.stat().st_size, 'sha256': sha(p)} for p in artifacts},
}
(root / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'artifact_and_source_checks_pass': report['artifact_and_source_checks_pass'],
                  'strict_18_case_display_regression_pass': report['strict_18_case_display_regression_pass'],
                  'status': report['status']}, indent=2))
if not report['artifact_and_source_checks_pass']:
    raise SystemExit('Saved model, source or sample provenance mismatch.')
