# Good
def compute_threshold_crossings(
    recording: si.BaseRecording,
    threshold_factor: float = 5.0,
    segment_index: int = 0,
) -> pd.DataFrame:
    """Return per-electrode crossing counts at threshold_factor x MAD.
    
    Parameters
    ----------
    recording : BaseRecording
        SpikeInterface recording with probe attached.
    threshold_factor : float
        Multiplier on MAD noise estimate. Typically 4 to 5.
    segment_index : int
        Which segment to process. Segments < 5 s are dropped upstream.

    Returns
    -------
    DataFrame with columns: electrode_id, n_crossings, rate_hz, mad_uv.
    """
    # MAD noise floor per channel, in uV (gain already applied)
    noise_mad: np.ndarray = si.get_noise_levels(recording, method="mad", return_scaled=True)
    threshold_uv = threshold_factor * noise_mad  # one threshold per channel

    # Crossings detected as negative-going excursions past threshold
    ...
	
# Bad (over-commented, types in comments not hints, verbose names)
def computeThresholdCrossingsForRecordingObject(
    inputRecordingObjectFromSpikeInterface,  # the recording object (BaseRecording)
    thresholdMultiplicationFactorForMAD,     # float, the multiplier
):
    # compute the noise floor using MAD
    # noise_floor_in_microvolts_per_channel: numpy ndarray of floats
    noise_floor_in_microvolts_per_channel = si.get_noise_levels(...)
    # multiply noise floor by threshold factor to get threshold
    threshold_value = thresholdMultiplicationFactorForMAD * noise_floor_in_microvolts_per_channel
    ...