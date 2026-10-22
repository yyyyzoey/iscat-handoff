"""W6: linear experiment input interface (fail-closed).

Accepts ONLY linear particle_ROI + matching background + metadata. Rejects
FFT demodulation amplitudes, abs(C), 8-bit display BMPs, and any missing
calibration field. It never claims experimental absolute diameter.
"""
from __future__ import annotations
import argparse, json, sys
import numpy as np

def infer(payload):
    reasons=[]
    obs=payload.get('observation_type')
    if obs!='LINEAR_PARTICLE_ROI_WITH_MATCHED_BACKGROUND':
        reasons.append('UNSUPPORTED_OBSERVATION_TYPE:'+str(obs))
    fmt=payload.get('encoding')
    if fmt in ('8BIT_DISPLAY_BMP','NONLINEAR_DISPLAY','FFT_400HZ_AMPLITUDE','FFT_DEMODULATED_MAGNITUDE'):
        reasons.append('FORBIDDEN_ENCODING:'+str(fmt))
    for k in ('particle_ROI_linear_intensity','background_linear_intensity','exposure_s',
              'total_magnification','camera_pixel_um','material_version'):
        if payload.get(k) is None:reasons.append('MISSING_FIELD:'+k)
    if reasons:
        return dict(candidate_D=None,reportable_D=None,diameter_reportable=False,
            reason_codes=reasons,compatible_D_components=None,
            scope='FAIL_CLOSED_INTERFACE_NO_ABSOLUTE_CALIBRATION')
    roi=np.asarray(payload['particle_ROI_linear_intensity'],float)
    bg=np.asarray(payload['background_linear_intensity'],float)
    if roi.shape!=bg.shape or roi.ndim!=2:reasons.append('SHAPE_MISMATCH_ROI_VS_BACKGROUND')
    if not (np.isfinite(roi).all() and np.isfinite(bg).all()):reasons.append('NONFINITE_INPUT')
    if np.any(roi<0) or np.any(bg<=0):reasons.append('NONPHYSICAL_LINEAR_INTENSITY')
    C=(roi-bg)/bg
    out=dict(observed_signed_C_checksum=float(np.sum(C)),
        candidate_D=None,reportable_D=None,diameter_reportable=False,
        compatible_D_components=None,
        reason_codes=reasons+['MATERIAL_N_K_NOT_CALIBRATED','ABSOLUTE_DIAMETER_NOT_EXPERIMENTALLY_VALIDATED',
            'REQUIRES_LOCKED_F2_QUALIFICATION_AND_DETECTION_PASS'],
        scope='CONDITIONAL_CANDIDATE_ONLY_PENDING_PHYSICS_GATE')
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',required=True);ap.add_argument('--schema-out',required=True)
    ap.add_argument('--example-out',required=True)
    a=ap.parse_args()
    payload=json.load(open(a.input,encoding='utf-8'))
    schema=dict(schema='iscat137.experiment_input.1',
        required_fields=['observation_type','particle_ROI_linear_intensity','background_linear_intensity',
            'exposure_s','total_magnification','camera_pixel_um','material_version'],
        accepted_observation_type='LINEAR_PARTICLE_ROI_WITH_MATCHED_BACKGROUND',
        forbidden_encodings=['8BIT_DISPLAY_BMP','NONLINEAR_DISPLAY','FFT_400HZ_AMPLITUDE','FFT_DEMODULATED_MAGNITUDE'],
        output_contract=['candidate_D','reportable_D','reason_codes','compatible_D_components'],
        fail_closed=True,
        absolute_diameter_validated=False)
    json.dump(schema,open(a.schema_out,'w',encoding='utf-8'),ensure_ascii=False,indent=2)
    results={'valid_linear_input':infer(payload)}
    bad=dict(payload);bad['observation_type']='FFT_400HZ_AMPLITUDE';bad['encoding']='FFT_DEMODULATED_MAGNITUDE'
    results['rejected_fft_amplitude_input']=infer(bad)
    bad2=dict(payload);bad2.pop('exposure_s');bad2['encoding']=None
    results['rejected_missing_exposure']=infer(bad2)
    json.dump(results,open(a.example_out,'w',encoding='utf-8'),ensure_ascii=False,indent=2)
    print('interface examples written; rejection codes:',
          results['rejected_fft_amplitude_input']['reason_codes'][:2])
if __name__=='__main__':main()
