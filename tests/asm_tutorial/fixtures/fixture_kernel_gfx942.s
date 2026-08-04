	.amdgcn_target "amdgcn-amd-amdhsa--gfx942"
	.text
	.globl	fixture_kernel
	.type	fixture_kernel,@function
fixture_kernel:
	s_load_dwordx4 s[0:3], s[4:5], 0x0
	s_waitcnt lgkmcnt(0)
	ds_read2_b64 v[2:5], v1 offset0:0 offset1:8
	v_mfma_f32_16x16x16_f16 a[0:3], v[2:3], v[4:5], a[0:3]
	s_endpgm
