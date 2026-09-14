function A = read_npy(path)
%READ_NPY Minimal NPY reader: plain little-endian numeric arrays, any shape.
%   Structured dtypes (e.g. the consensus sortings' spikes.npy) are NOT
%   supported - read those via Python/spikeinterface, or ask for a split
%   export. C-order arrays are permuted to MATLAB layout.
%READ_NPY Plain-dtype NPY reader: little-endian f4/f8/i2/i4/i8/u1, any shape.
fid = fopen(path, "r"); c = onCleanup(@() fclose(fid));
magic = fread(fid, 6, "uint8=>uint8")';
assert(isequal(magic, [147 'NUMPY']), "not an NPY file");
ver = fread(fid, 2, "uint8");
if ver(1) >= 2, hlen = fread(fid, 1, "uint32");
else,           hlen = fread(fid, 1, "uint16");
end
hdr = fread(fid, hlen, "uint8=>char")';
descr = regexp(hdr, "'descr':\s*'([^']+)'", "tokens", "once");
shape = regexp(hdr, "'shape':\s*\(([^)]*)\)", "tokens", "once");
fortran = contains(hdr, "'fortran_order': True");
dims = sscanf(strrep(shape{1}, ",", " "), "%d")';
if isempty(dims), dims = 1; end
map = struct("f4", "single", "f8", "double", "i2", "int16", ...
             "i4", "int32", "i8", "int64", "u1", "uint8");
d = descr{1};
assert(d(1) == '<' || d(1) == '|', "big-endian npy unsupported: %s", d);
A = fread(fid, prod(dims), map.(d(2:end)) + "=>" + map.(d(2:end)));
if numel(dims) > 1
    if fortran, A = reshape(A, dims);
    else,       A = permute(reshape(A, fliplr(dims)), numel(dims):-1:1);
    end
end
end
