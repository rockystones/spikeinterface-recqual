function A = read_npz_array(npzPath, member)
%READ_NPZ_ARRAY Extract one array from an .npz (a zip of .npy members).
%   A = READ_NPZ_ARRAY(path, "wf") for the giant-waveform shards under
%   data/derived/rocky/giant_wf_shards/. Uses read_npy; plain numeric
%   little-endian dtypes only (f4/f8/i2/i4/i8/u1).
%READ_NPZ_ARRAY Extract one array from an .npz (a zip of .npy files).
tmp = tempname; mkdir(tmp);
cleaner = onCleanup(@() rmdir(tmp, "s"));
unzip(npzPath, tmp);
A = read_npy(fullfile(tmp, member + ".npy"));
end
