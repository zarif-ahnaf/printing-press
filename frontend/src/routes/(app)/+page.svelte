<script lang="ts">
	import { onMount } from 'svelte';
	import { Palette, Zap, ShieldCheck, ArrowRight, FileText } from 'lucide-svelte';

	// Animation states with proper types
	let progress = $state(0);
	let isScrolled = $state(false);
	let featureRevealed = $state(false);
	let ctaRevealed = $state(false);
	let circuitProgress = $state(0);
	let dots = $state<number[]>(Array(25).fill(0));
	let paperType = $state<'matte' | 'glossy' | 'textured' | 'recycled'>('matte');
	let printPressActive = $state(false);
	import { Button } from '$lib/components/ui/button';
	let mouseX = $state(0);
	let mouseY = $state(0);
	let paper3D = $state({ rotateX: 0, rotateY: 0, scale: 1 });
	let printPlanePosition = $state({ x: 0, y: 0 });

	// Element references with proper types
	let printPressElement: HTMLElement | null = null;
	let circuitSection: HTMLElement | null = null;
	let featureSection: HTMLElement | null = null;
	let ctaSection: HTMLElement | null = null;

	// Mouse movement handler with type annotations
	const handleMouseMove = (e: MouseEvent) => {
		mouseX = e.clientX;
		mouseY = e.clientY;

		// Update 3D paper position
		const centerX = window.innerWidth / 2;
		const centerY = window.innerHeight / 2;

		paper3D = {
			rotateX: (centerY - mouseY) / 30,
			rotateY: (mouseX - centerX) / 30,
			scale: 1 + Math.min(0.2, Math.abs((centerX - mouseX) / window.innerWidth))
		};

		// Update paper plane position
		printPlanePosition = {
			x: (mouseX / window.innerWidth) * 100 - 50,
			y: (mouseY / window.innerHeight) * 100 - 50
		};
	};

	// Scroll handling with proper types
	const handleScroll = () => {
		const scrollY = window.scrollY;
		const max = document.body.scrollHeight - window.innerHeight;
		progress = Math.min(scrollY / max, 1);

		// Track sections for reveal animations
		if (featureSection) {
			const featureRect = featureSection.getBoundingClientRect();
			featureRevealed = featureRect.top < window.innerHeight * 0.7;
		}

		if (ctaSection) {
			const ctaRect = ctaSection.getBoundingClientRect();
			ctaRevealed = ctaRect.top < window.innerHeight * 0.7;
		}

		// Circuit path animation
		if (circuitSection) {
			const circuitRect = circuitSection.getBoundingClientRect();
			const circuitHeight = circuitSection.offsetHeight;
			circuitProgress = Math.max(
				0,
				Math.min(1, (circuitRect.top - window.innerHeight * 0.3) / (circuitHeight * 0.7))
			);
		}

		isScrolled = scrollY > 100;

		// Animate print press when visible
		if (printPressElement) {
			const rect = printPressElement.getBoundingClientRect();
			printPressActive = rect.top < window.innerHeight && rect.bottom > 0;
		}
	};

	onMount(() => {
		window.addEventListener('mousemove', handleMouseMove);
		window.addEventListener('scroll', handleScroll);
		handleScroll(); // Initial call

		// Staggered dot animation
		dots.forEach((_, i) => {
			setTimeout(
				() => {
					dots[i] = 1;
				},
				i * 30 + 200
			);
		});

		return () => {
			window.removeEventListener('mousemove', handleMouseMove);
			window.removeEventListener('scroll', handleScroll);
		};
	});
</script>

<!-- Hero Section with 3D Printing Press -->
<section class="relative flex min-h-screen items-center overflow-hidden">
	<!-- Paper texture background as SVG -->
	<svg
		class="absolute inset-0 -z-10 h-full w-full opacity-10"
		xmlns="http://www.w3.org/2000/svg"
		width="50"
		height="50"
		viewBox="0 0 50 50"
	>
		<pattern
			id="paper"
			width="50"
			height="50"
			patternUnits="userSpaceOnUse"
			patternTransform="rotate(15)"
		>
			<rect x="0" y="0" width="50" height="50" fill="transparent" />
			<path
				d="M0 25h50M10 0 L10 50M20 10 L20 40M30 0 L30 50M40 10 L40 40"
				stroke-width="0.5"
				stroke="hsl(var(--border))"
				opacity="0.1"
			/>
			<path
				d="M1 15h48M1 35 h48M15 0 L15 50M35 0 L35 50"
				stroke-width="0.5"
				stroke="hsl(var(--border))"
				opacity="0.05"
			/>
		</pattern>
		<rect width="100%" height="100%" fill="url(#paper)" />
	</svg>

	<div class="relative z-10 container mx-auto px-4 py-24">
		<div class="mx-auto max-w-4xl text-center">
			<h1
				class="mb-6 bg-linear-to-r from-foreground to-muted-foreground bg-clip-text text-4xl font-bold text-transparent md:text-6xl"
			>
				Premium <span
					class="after:animate-wave relative inline-block after:absolute after:-bottom-1 after:left-0 after:h-1 after:w-full after:rounded after:bg-linear-to-r after:from-primary after:to-primary/80"
					>Printing</span
				> Services
			</h1>
			<p class="mx-auto mb-10 max-w-3xl text-xl text-muted-foreground">
				High-quality printing with lightning-fast turnaround. Perfect for businesses, creators, and
				events.
			</p>
			<div class="flex flex-col justify-center gap-4 sm:flex-row">
				<Button size="lg" variant="default" href="/upload">
					Get Started
					<ArrowRight class="ml-2 h-4 w-4" />
				</Button>
			</div>
		</div>

		<!-- 3D Paper Stack -->
		<div class="perspective-1000 mt-20 flex justify-center">
			<div
				class="transform-style-preserve-3d w-full max-w-3xl"
				style="transform: rotateX({paper3D.rotateX}deg) rotateY({paper3D.rotateY}deg) scale({paper3D.scale});"
				bind:this={printPressElement}
			>
				<!-- Base -->
				<div class="flex h-16 items-center justify-center rounded-t-xl bg-muted">
					<div class="h-1/2 w-2/3 rounded-b-xl border border-border bg-card"></div>
				</div>

				<!-- Press body -->
				<div class="relative h-64">
					<!-- Press frame -->
					<div class="absolute left-1/4 h-56 w-4 bg-border"></div>
					<div class="absolute right-1/4 h-56 w-4 bg-border"></div>

					<!-- Press arm -->
					<div
						class="absolute top-0 h-8 w-full rounded-b-xl border border-border bg-card"
						style="transform: {printPressActive
							? 'translateY(' + Math.sin(Date.now() / 1000) * 20 + 'px)'
							: 'translateY(0)'}; transition: transform 0.3s"
					>
						<div class="mx-auto h-full w-1/2 rounded-b-xl bg-muted"></div>
					</div>

					<!-- 3D Paper stack -->
					<div
						class="transform-style-preserve-3d absolute top-8 left-1/6 flex h-48 w-2/3 items-center justify-center rounded-xl border border-border bg-background"
					>
						<div
							class="transform-style-preserve-3d flex h-11/12 w-11/12 items-center justify-center rounded-lg bg-card p-4"
						>
							<!-- Multiple paper layers -->
							{#each [0, 1, 2, 3] as layer}
								<div
									class="absolute h-full w-full rounded-lg transition-all duration-700"
									style="transform: translateZ({-layer * 5}px);"
								>
									<div
										class="h-full w-full rounded-lg {paperType === 'matte'
											? 'bg-[#F5F5F5]'
											: paperType === 'glossy'
												? 'bg-[#F0F0F0]'
												: paperType === 'textured'
													? 'bg-[#E8E8E8]'
													: 'bg-[#E0E0E0]'} border border-border"
									></div>
								</div>
							{/each}

							<!-- Paper content -->
							<div class="flex h-3/4 w-3/4 items-center justify-center rounded-md bg-white">
								<div class="text-4xl font-bold text-primary">3D</div>
							</div>
						</div>
					</div>

					<!-- Ink rollers -->
					<div class="absolute bottom-8 left-1/8 flex h-6 w-3/4 rounded-full bg-muted">
						{#each [1, 2, 3] as _, i}
							<div class="flex h-full w-1/3 items-center justify-center">
								<div
									class="animate-rotate h-4 w-4/5 rounded-full bg-primary"
									style="animation-delay: {i * 0.5}s; animation-duration: {5 - i}s"
								></div>
							</div>
						{/each}
					</div>
				</div>
			</div>
		</div>

		<!-- 3D Paper Plane -->
		<div class="mt-12 flex justify-center">
			<div
				class="transform-style-preserve-3d relative h-16 w-32"
				style="transform: translateX({printPlanePosition.x}%) translateY({printPlanePosition.y}%) rotateY({-printPlanePosition.x}deg) rotateX({printPlanePosition.y}deg); transition: transform 0.3s;"
			>
				<div
					class="transform-style-preserve-3d absolute h-4 w-full rounded-t-lg bg-primary"
					style="transform: translateZ(2px) rotateX(-5deg);"
				></div>
				<div
					class="transform-style-preserve-3d absolute h-12 w-full rounded-lg bg-card"
					style="transform: translateZ(0px);"
				></div>
				<div
					class="transform-style-preserve-3d absolute h-4 w-full rounded-b-lg bg-primary"
					style="transform: translateZ(-2px) rotateX(5deg);"
				></div>
			</div>
		</div>

		<!-- Paper type selector -->
		<div class="mt-12 text-center">
			<div class="inline-flex space-x-4 rounded-lg bg-card p-2">
				{#each ['matte', 'glossy', 'textured', 'recycled'] as type}
					<button
						onclick={() => (paperType = type as typeof paperType)}
						class="rounded-md px-3 py-1 transition-all duration-300 {paperType === type
							? 'bg-primary font-medium text-primary-foreground'
							: 'text-muted-foreground hover:text-foreground'}"
						aria-label={`Select ${type} paper type`}
						tabindex="0"
					>
						{type.charAt(0).toUpperCase() + type.slice(1)}
					</button>
				{/each}
			</div>
		</div>
	</div>
</section>

<!-- 3D Circuit Section -->
<section class="py-20" bind:this={circuitSection}>
	<div class="container mx-auto px-4">
		<div class="mb-16 text-center">
			<h2 class="mb-4 text-3xl font-bold text-foreground">Our Print Journey</h2>
			<p class="mx-auto max-w-2xl text-lg text-muted-foreground">
				From upload to doorstep — perfected through precision and care
			</p>
		</div>

		<div class="relative mx-auto max-w-4xl">
			<div class="flex h-64 items-center justify-center">
				<svg viewBox="0 0 800 200" class="h-auto w-full" style="transform: translateY(20px);">
					<!-- Base circuit line -->
					<path
						d="M 50 100 Q 200 40, 350 100 Q 500 160, 650 100"
						fill="none"
						stroke="hsl(var(--border))"
						stroke-width="2"
						stroke-dasharray="10,10"
					/>

					<!-- Animated circuit line -->
					<path
						d="M 50 100 Q 200 40, 350 100 Q 500 160, 650 100"
						fill="none"
						stroke="url(#grad)"
						stroke-width="3"
						class="stroke-primary"
						style="stroke-dasharray: 1000; stroke-dashoffset: calc(1000 * (1 - {circuitProgress}));"
					/>

					<!-- Circuit line animation gradient -->
					<defs>
						<linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="0%">
							<stop offset="0%" stop-color="hsl(var(--primary))" />
							<stop offset="100%" stop-color="hsl(var(--primary) / 0.8)" />
						</linearGradient>

						<!-- Paper texture pattern for circuit -->
						<pattern id="paper-texture" width="20" height="20" patternUnits="userSpaceOnUse">
							<rect width="100%" height="100%" fill="hsl(var(--background))" />
							<path
								d="M 0 0 L 20 20 M 20 0 L 0 20"
								stroke="hsl(var(--border))"
								stroke-width="0.2"
								opacity="0.2"
							/>
						</pattern>
					</defs>

					<!-- Moving dot along path -->
					<circle
						cx={50 + (1 - circuitProgress) * 600}
						cy={100 + Math.sin((1 - circuitProgress) * Math.PI * 2) * 30}
						r="8"
						fill="hsl(var(--primary))"
						class="drop-shadow-sm"
					/>

					<!-- Paper texture on circuit -->
					<rect
						x="50"
						y="85"
						width="600"
						height="30"
						fill="url(#paper-texture)"
						opacity="0.3"
						rx="15"
					/>
				</svg>
			</div>

			<!-- Process steps with 3D effect -->
			<div class="perspective-1000 mt-12 flex justify-between text-center">
				{#each ['Upload', 'Proof', 'Print', 'Ship'] as step, i}
					<div
						class="transform-style-preserve-3d flex flex-col items-center"
						style="transform: translateZ({Math.abs(i - 2) * 20}px);"
					>
						<div
							class="mb-2 flex h-12 w-12 items-center justify-center rounded-full border-2 border-border bg-muted font-medium text-foreground"
						>
							{i + 1}
						</div>
						<span class="font-medium text-foreground">{step}</span>
					</div>
				{/each}
			</div>
		</div>
	</div>
</section>

<!-- 3D Paper Types Section -->
<section class="py-24">
	<div class="container mx-auto px-4">
		<div class="mb-16 text-center">
			<h2 class="mb-4 text-3xl font-bold text-foreground">Premium Paper Selection</h2>
			<p class="mx-auto max-w-2xl text-lg text-muted-foreground">
				Choose from our extensive collection of high-quality paper stocks
			</p>
		</div>

		<div class="mx-auto max-w-4xl">
			<!-- 3D Paper stack -->
			<div class="perspective-1000 relative mb-12 h-64">
				{#each [1, 2, 3, 4] as layer}
					<div
						class="absolute h-44 w-full rounded-xl transition-all duration-500 {paperType ===
						'matte'
							? 'bg-[#F5F5F5]'
							: paperType === 'glossy'
								? 'bg-[#F0F0F0]'
								: paperType === 'textured'
									? 'bg-[#E8E8E8]'
									: 'bg-[#E0E0E0]'}"
						style="left: {layer * 10}px; top: {layer * 10}px; z-index: {5 -
							layer}; opacity: {paperType === 'matte'
							? 1 - layer * 0.1
							: paperType === 'glossy'
								? 0.9 - layer * 0.1
								: paperType === 'textured'
									? 0.8 - layer * 0.1
									: 0.7 - layer * 0.1}; transform: translateZ({-layer * 10}px);"
					></div>
				{/each}

				<!-- Paper type indicator -->
				<div class="absolute top-0 left-0 flex h-full w-full items-center justify-center">
					<div class="rounded-lg border border-border bg-background p-4 text-center">
						<div class="mb-1 font-bold text-foreground">
							{paperType === 'matte'
								? 'Matte'
								: paperType === 'glossy'
									? 'Glossy'
									: paperType === 'textured'
										? 'Textured'
										: 'Recycled'}
						</div>
						<div class="text-sm text-muted-foreground">
							{paperType === 'matte'
								? 'Smooth finish, excellent for photos'
								: paperType === 'glossy'
									? 'High shine, vibrant colors'
									: paperType === 'textured'
										? 'Elegant texture, premium feel'
										: 'Eco-friendly, sustainable option'}
						</div>
					</div>
				</div>
			</div>

			<!-- Paper options -->
			<div class="grid grid-cols-1 gap-8 md:grid-cols-3">
				<div class="rounded-xl border border-border bg-card p-6">
					<div class="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-muted">
						<span class="text-2xl">M</span>
					</div>
					<h3 class="mb-2 text-xl font-bold text-foreground">Matte Paper</h3>
					<p class="mb-4 text-muted-foreground">
						Smooth finish with no glare, excellent for photos and reading materials
					</p>
					<div class="flex items-center gap-2">
						<div class="h-2 w-12 bg-[#F5F5F5]"></div>
						<div class="text-sm text-muted-foreground">100 gsm</div>
					</div>
				</div>

				<div class="rounded-xl border border-border bg-card p-6">
					<div class="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-muted">
						<span class="text-2xl">G</span>
					</div>
					<h3 class="mb-2 text-xl font-bold text-foreground">Glossy Paper</h3>
					<p class="mb-4 text-muted-foreground">
						High shine finish that makes colors pop and appear more vibrant
					</p>
					<div class="flex items-center gap-2">
						<div class="h-2 w-12 bg-[#F0F0F0]"></div>
						<div class="text-sm text-muted-foreground">150 gsm</div>
					</div>
				</div>

				<div class="rounded-xl border border-border bg-card p-6">
					<div class="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-muted">
						<span class="text-2xl">R</span>
					</div>
					<h3 class="mb-2 text-xl font-bold text-foreground">Recycled Paper</h3>
					<p class="mb-4 text-muted-foreground">
						Eco-friendly option with a natural texture that shows your commitment
					</p>
					<div class="flex items-center gap-2">
						<div class="h-2 w-12 bg-[#E0E0E0]"></div>
						<div class="text-sm text-muted-foreground">120 gsm</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</section>

<!-- Features Section -->
<section class="bg-muted py-24" bind:this={featureSection}>
	<div class="container mx-auto px-4">
		<div class="mb-16 text-center">
			<h2 class="mb-4 text-3xl font-bold text-foreground">Why Choose Us</h2>
			<p class="mx-auto max-w-2xl text-lg text-muted-foreground">
				We combine cutting-edge technology with artisan craftsmanship
			</p>
		</div>

		<div class="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-4">
			{#each [{ icon: Palette, title: 'Vibrant Colors', desc: 'Pantone-matched inks for perfect brand consistency' }, { icon: Zap, title: 'Lightning Fast', desc: 'Same-day printing for most orders' }, { icon: ShieldCheck, title: 'Quality Guaranteed', desc: '100% satisfaction guarantee' }, { icon: FileText, title: 'Custom Packaging', desc: 'Tailored packaging for your products' }] as feature, i}
				<div
					class="rounded-xl border border-border bg-card p-6 transition-all duration-300 hover:border-border hover:shadow-md {featureRevealed
						? 'translate-y-0 opacity-100'
						: 'translate-y-10 opacity-0'} transform-style-preserve-3d"
					style="transition-delay: {i * 100}ms; transform: translateZ({i * 10}px);"
					role="region"
					aria-label="Feature: {feature.title}"
				>
					<div class="mb-6 flex h-14 w-14 items-center justify-center rounded-lg bg-muted">
						<feature.icon class="h-7 w-7 text-foreground" />
					</div>
					<h3 class="mb-3 text-xl font-bold text-foreground">{feature.title}</h3>
					<p class="text-muted-foreground">{feature.desc}</p>
				</div>
			{/each}
		</div>
	</div>
</section>

<!-- CTA Section -->
<section class="bg-background py-20 text-foreground" bind:this={ctaSection}>
	<div class="container mx-auto px-4 text-center">
		<div
			class="{ctaRevealed
				? 'translate-y-0 opacity-100'
				: 'translate-y-10 opacity-0'} transform-style-preserve-3d transition-all duration-700"
			style="transform: translateZ(50px);"
		>
			<h2 class="mb-6 text-4xl font-bold">Ready to Bring Your Ideas to Life?</h2>
			<p class="mb-10 text-xl text-muted-foreground">
				Join thousands of satisfied customers who trust us with their most important prints
			</p>

			<!-- 3D satisfaction rating -->
			<div class="mt-12 flex justify-center">
				<div
					class="transform-style-preserve-3d relative flex h-32 w-64 items-center justify-center overflow-hidden rounded-xl border border-border bg-card"
				>
					<div
						class="rotateY(45deg) absolute -bottom-4 -left-4 h-24 w-24 transform rounded-full bg-primary opacity-20"
					></div>
					<div
						class="rotateX(-30deg) absolute -top-4 -right-4 h-20 w-20 transform rounded-full bg-primary opacity-20"
					></div>
					<div class="text-center">
						<div class="text-3xl font-bold text-primary">99.9%</div>
						<div class="text-muted-foreground">Customer Satisfaction</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</section>

<!-- Footer -->
<footer class="border-t border-border bg-background py-12 text-muted-foreground">
	<div class="container mx-auto px-4 text-center">
		<p>© {new Date().getFullYear()} PrintPro Services. All rights reserved.</p>
	</div>
</footer>

<!-- Tailwind animations -->
<style>
	@keyframes float {
		0%,
		100% {
			transform: translateY(0px);
		}
		50% {
			transform: translateY(-10px);
		}
	}

	@keyframes wave {
		0%,
		100% {
			transform: translateX(0) scaleX(0.5);
		}
		50% {
			transform: translateX(100%) scaleX(1);
		}
	}

	@keyframes rotate {
		0% {
			transform: rotate(0deg);
		}
		100% {
			transform: rotate(360deg);
		}
	}

	.animate-rotate {
		animation: rotate 10s linear infinite;
	}
</style>
