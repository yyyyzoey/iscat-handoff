"""Conservative measurement gates. No validator labels permitted."""
def reportable(candidate,*,detected=False,forward_qualified=False,optimizer_complete=False,profile_complete=False,model_error_qualified=False,camera_qualified=False,interior=False,competing=False,unsearched=True):
    reasons=[]
    if candidate is None: reasons.append('NO_CANDIDATE')
    if not detected: reasons.append('NOT_DETECTED')
    if not forward_qualified: reasons.append('FORWARD_NOT_QUALIFIED')
    if not optimizer_complete: reasons.append('OPTIMIZER_NOT_COMPLETE')
    if not profile_complete: reasons.append('PROFILE_INCOMPLETE')
    if not model_error_qualified: reasons.append('MODEL_ERROR_NOT_QUALIFIED')
    if not camera_qualified: reasons.append('CAMERA_SIZING_NOT_QUALIFIED')
    if not interior: reasons.append('BOUNDARY_OR_DOMAIN_UNRESOLVED')
    if competing: reasons.append('COMPETING_DIAMETERS')
    if unsearched: reasons.append('UNSEARCHED_DIAMETER_REGIONS')
    return {'candidate_D':candidate,'reportable_D':candidate if not reasons else None,'reason_codes':reasons}
