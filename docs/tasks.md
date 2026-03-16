# Simulation Tasks

All 30 available tasks, grouped by category. Each task is a Python function in `tasks/<category>/` with signature:

```python
def run(payload: dict, progress_cb: Callable[[float], None]) -> dict: ...
```

Call `progress_cb(0.0–1.0)` periodically to report progress. Return a dict as the result.

---

## Monte Carlo Simulations

### `monte_carlo_pi`
Estimates π by sampling random points in a unit square and checking if they fall inside the unit circle.

| Payload Field | Type | Default | Description |
|--------------|------|---------|-------------|
| `iterations` | int | 1,000,000 | Random points to sample |

**Result:**
| Field | Description |
|-------|-------------|
| `pi_estimate` | Estimated value of π |
| `error` | Absolute error vs true π |
| `iterations` | Iterations run |

---

### `option_pricing`
Prices a European call option using Black-Scholes Monte Carlo (geometric Brownian motion paths).

| Payload Field | Type | Default | Description |
|--------------|------|---------|-------------|
| `S` | float | 100.0 | Current stock price |
| `K` | float | 100.0 | Strike price |
| `T` | float | 1.0 | Time to maturity (years) |
| `r` | float | 0.05 | Risk-free rate |
| `sigma` | float | 0.2 | Volatility |
| `simulations` | int | 500,000 | Number of MC paths |
| `steps` | int | 252 | Time steps per path |

**Result:** `price`, `variance`, `std_error`, echoed input params

---

### `random_walk`
Simulates N particles doing independent random walks in D-dimensional space.

| Payload Field | Type | Default | Description |
|--------------|------|---------|-------------|
| `steps` | int | 1,000 | Steps per walk |
| `particles` | int | 100 | Number of particles |
| `dimensions` | int | 2 | 1, 2, or 3 |

**Result:** `final_positions`, `mean_displacement`, `max_displacement`

---

### `monte_carlo_integration`
Numerically integrates a function over [a, b] via Monte Carlo sampling.

| Payload Field | Type | Default | Description |
|--------------|------|---------|-------------|
| `samples` | int | 1,000,000 | Sample count |
| `function` | str | "sin" | `sin`, `cos`, `exp`, `x2`, `x3`, `sqrt` |
| `a` | float | 0.0 | Lower bound |
| `b` | float | π | Upper bound |

**Result:** `integral`, echoed `function`, `a`, `b`, `samples`

---

## Heat & Diffusion

### `heat_diffusion_1d`
Solves the 1D heat equation using explicit finite differences (Dirichlet boundary conditions, temperature=0 at both ends).

| Payload Field | Type | Default | Description |
|--------------|------|---------|-------------|
| `n_points` | int | 200 | Grid points |
| `steps` | int | 5,000 | Time steps |
| `diffusion_coeff` | float | 0.1 | Thermal diffusivity α |

**Result:** `max_temp`, `mean_temp`, `final_profile` (list)

---

### `heat_diffusion_2d`
Solves the 2D heat equation on a square grid using explicit finite differences.

| Payload Field | Type | Default | Description |
|--------------|------|---------|-------------|
| `grid_size` | int | 50 | Grid resolution (N×N) |
| `steps` | int | 500 | Time steps |
| `diffusion_coeff` | float | 0.1 | Thermal diffusivity |

**Result:** `max_temp`, `mean_temp`, `final_grid` (2D list)

---

### `chemical_diffusion`
2D diffusion of a chemical species with a point source at the center of the grid.

| Payload Field | Type | Default | Description |
|--------------|------|---------|-------------|
| `grid_size` | int | 100 | Grid resolution |
| `steps` | int | 2,000 | Time steps |
| `diffusion_coeff` | float | 0.05 | Diffusion coefficient |

**Result:** `max_concentration`, `total_mass`, `final_grid` (2D list)

---

### `population_spread`
Models population dispersal via diffusion with logistic growth (Fisher-KPP equation).

| Payload Field | Type | Default | Description |
|--------------|------|---------|-------------|
| `grid_size` | int | 80 | Grid resolution |
| `steps` | int | 1,000 | Time steps |
| `diffusion_coeff` | float | 0.05 | Diffusion rate |
| `growth_rate` | float | 0.1 | Logistic growth rate |
| `carrying_capacity` | float | 1.0 | Max population density |

**Result:** `total_population`, `occupied_cells`, `max_density`, `final_grid` (2D list)

---

## Linear Algebra

### `matrix_multiply`
Benchmarks dense N×N matrix multiplication using NumPy.

| Payload Field | Type | Default | Description |
|--------------|------|---------|-------------|
| `size` | int | 512 | Matrix dimension |

**Result:** `elapsed_ms`, `checksum`

---

### `eigenvalue_decomp`
Computes eigenvalues and eigenvectors of a random symmetric positive semi-definite matrix.

| Payload Field | Type | Default | Description |
|--------------|------|---------|-------------|
| `size` | int | 256 | Matrix dimension |

**Result:** `largest_eigenvalue`, `smallest_eigenvalue`, `top_5_eigenvalues`, `spectral_gap`, `trace`

---

### `svd_decomposition`
Full Singular Value Decomposition of a random M×N matrix.

| Payload Field | Type | Default | Description |
|--------------|------|---------|-------------|
| `rows` | int | 512 | Matrix rows |
| `cols` | int | 256 | Matrix columns |

**Result:** `rank`, `top_5_singular_values`, `largest_singular_value`, `frobenius_norm`, `top5_explained_variance_ratio`

---

### `pca_covariance`
Principal Component Analysis on synthetic high-dimensional data via covariance eigendecomposition.

| Payload Field | Type | Default | Description |
|--------------|------|---------|-------------|
| `n_samples` | int | 1,000 | Data points |
| `n_features` | int | 50 | Feature dimensions |
| `n_components` | int | 10 | PCA components to extract |

**Result:** `explained_variance_ratios`, `cumulative_explained_variance`, `top_eigenvalues`

---

## Physics / Kinematics

### `projectile_motion`
Projectile trajectory with quadratic air drag, integrated via Euler method.

| Payload Field | Type | Default | Description |
|--------------|------|---------|-------------|
| `initial_velocity` | float | 50.0 | Launch speed (m/s) |
| `angle_deg` | float | 45.0 | Launch angle (degrees) |
| `drag_coeff` | float | 0.01 | Drag coefficient |
| `mass` | float | 1.0 | Mass (kg) |
| `dt` | float | 0.01 | Time step (s) |
| `max_steps` | int | 10,000 | Max integration steps |

**Result:** `range_m`, `max_height_m`, `flight_time_s`

---

### `lotka_volterra`
Predator-prey population dynamics using Lotka-Volterra ODEs integrated with RK4.

| Payload Field | Type | Default | Description |
|--------------|------|---------|-------------|
| `prey_initial` | float | 40.0 | Initial prey count |
| `predator_initial` | float | 9.0 | Initial predator count |
| `alpha` | float | 0.1 | Prey growth rate |
| `beta` | float | 0.02 | Predation rate |
| `delta` | float | 0.01 | Predator efficiency |
| `gamma` | float | 0.1 | Predator death rate |
| `steps` | int | 10,000 | Integration steps |
| `dt` | float | 0.01 | Time step |

**Result:** `prey_mean`, `predator_mean`, `prey_max`, `predator_max`, `final_prey`, `final_predator`, `prey_history`, `predator_history`

---

### `pendulum_motion`
Damped nonlinear pendulum integrated with RK4.

| Payload Field | Type | Default | Description |
|--------------|------|---------|-------------|
| `length` | float | 1.0 | Pendulum length (m) |
| `mass` | float | 1.0 | Bob mass (kg) |
| `damping` | float | 0.1 | Damping coefficient |
| `initial_angle_deg` | float | 30.0 | Starting angle (degrees) |
| `initial_omega` | float | 0.0 | Initial angular velocity (rad/s) |
| `steps` | int | 10,000 | Integration steps |
| `dt` | float | 0.005 | Time step |

**Result:** `final_angle_deg`, `initial_energy`, `final_energy`, `energy_dissipated`, `theta_history_deg`

---

### `spring_mass`
Damped harmonic oscillator (spring-mass) integrated with RK4.

| Payload Field | Type | Default | Description |
|--------------|------|---------|-------------|
| `mass` | float | 1.0 | Mass (kg) |
| `spring_constant` | float | 10.0 | Spring constant k (N/m) |
| `damping` | float | 0.5 | Damping coefficient |
| `initial_displacement` | float | 1.0 | Initial position (m) |
| `initial_velocity` | float | 0.0 | Initial velocity (m/s) |
| `steps` | int | 5,000 | Integration steps |
| `dt` | float | 0.01 | Time step |

**Result:** `natural_frequency_hz`, `max_displacement`, `min_displacement`, `final_displacement`, `position_history`

---

## Fluid & Network

### `fluid_advection`
Particle advection in a 2D divergence-free velocity field using RK4, with periodic boundary conditions.

| Payload Field | Type | Default | Description |
|--------------|------|---------|-------------|
| `n_particles` | int | 200 | Particle count |
| `steps` | int | 500 | Time steps |
| `dt` | float | 0.05 | Time step |
| `domain` | float | 2π | Domain size |

**Result:** `mean_displacement`, `max_displacement`, `final_positions`

---

### `network_spread`
SIR disease/information spread on a random Erdős-Rényi graph.

| Payload Field | Type | Default | Description |
|--------------|------|---------|-------------|
| `n_nodes` | int | 500 | Number of nodes |
| `avg_degree` | float | 6.0 | Average node degree |
| `infection_prob` | float | 0.3 | Transmission probability per contact per step |
| `recovery_prob` | float | 0.1 | Recovery probability per step |
| `steps` | int | 100 | Time steps |
| `initial_infected` | int | 5 | Initially infected nodes |

**Result:** `peak_infected`, `final_susceptible`, `final_infected`, `final_recovered`, `S_history`, `I_history`, `R_history`

---

### `traffic_flow`
1D traffic simulation using the Nagel-Schreckenberg cellular automaton.

| Payload Field | Type | Default | Description |
|--------------|------|---------|-------------|
| `road_length` | int | 200 | Road length (cells) |
| `n_vehicles` | int | 80 | Vehicle count |
| `v_max` | int | 5 | Maximum speed |
| `p_brake` | float | 0.3 | Random braking probability |
| `steps` | int | 1,000 | Time steps |

**Result:** `density`, `mean_velocity`, `mean_flow`, `final_mean_velocity`, `velocity_history`

---

### `forest_fire`
Stochastic forest-fire cellular automaton. Trees grow randomly and ignite from neighbors or spontaneously.

| Payload Field | Type | Default | Description |
|--------------|------|---------|-------------|
| `grid_size` | int | 100 | Grid resolution |
| `steps` | int | 500 | Time steps |
| `p_grow` | float | 0.05 | Tree regrowth probability per cell per step |
| `p_ignite` | float | 0.001 | Spontaneous ignition probability |
| `p_tree` | float | 0.6 | Initial tree density |

**Result:** `total_burned`, `peak_burning`, `final_tree_count`, `final_burning`, `burned_per_step`

---

## Additional

### `diffusion_reaction`
Gray-Scott reaction-diffusion system — produces Turing-like patterns from two interacting chemical species.

| Payload Field | Type | Default | Description |
|--------------|------|---------|-------------|
| `grid_size` | int | 80 | Grid resolution |
| `steps` | int | 2,000 | Time steps |
| `Du` | float | 0.16 | Diffusion rate of U |
| `Dv` | float | 0.08 | Diffusion rate of V |
| `f` | float | 0.035 | Feed rate |
| `k` | float | 0.065 | Kill rate |

**Result:** `mean_U`, `mean_V`, `pattern_variance_V`, `final_U_grid`, `final_V_grid`

---

### `quantum_well`
Solves the time-independent Schrödinger equation for a particle in a finite square well using matrix diagonalization.

| Payload Field | Type | Default | Description |
|--------------|------|---------|-------------|
| `n_points` | int | 1,000 | Grid points |
| `well_depth` | float | 50.0 | Well depth (eV) |
| `well_width` | float | 2.0 | Well width (nm) |

**Result:** `n_bound_states`, `ground_state_energy_eV`, `bound_state_energies_eV`, `ground_state_wavefunction`

---

### `brownian_motion`
Stochastic Brownian motion with mean-squared displacement (MSD) tracking and comparison to theory.

| Payload Field | Type | Default | Description |
|--------------|------|---------|-------------|
| `n_particles` | int | 200 | Particle count |
| `steps` | int | 1,000 | Time steps |
| `dt` | float | 0.01 | Time step |
| `diffusion_coeff` | float | 1.0 | Diffusion coefficient D |
| `dimensions` | int | 2 | 1, 2, or 3 |

**Result:** `final_msd`, `theoretical_msd` (= 2·D·t·d), `msd_ratio`, `msd_history`

---

### `heat_conduction_varying`
1D heat conduction with spatially varying thermal conductivity (step, linear, or Gaussian profiles).

| Payload Field | Type | Default | Description |
|--------------|------|---------|-------------|
| `n_points` | int | 200 | Grid points |
| `steps` | int | 5,000 | Time steps |
| `conductivity_profile` | str | "step" | `step`, `linear`, `gaussian` |

**Result:** `max_conductivity`, `max_temp`, `mean_temp`, `final_profile`

---

### `fractal_dla`
Diffusion-Limited Aggregation: particles released from the edge walk randomly until they stick to a growing cluster. Estimates fractal dimension.

| Payload Field | Type | Default | Description |
|--------------|------|---------|-------------|
| `grid_size` | int | 200 | Grid resolution |
| `n_particles` | int | 2,000 | Particles to aggregate |
| `max_walk_steps` | int | 10,000 | Max steps per particle |

**Result:** `cluster_size`, `estimated_fractal_dimension`, `grid` (binary 2D list)

---

### `wave_propagation`
1D or 2D wave equation solved via explicit finite differences.

| Payload Field | Type | Default | Description |
|--------------|------|---------|-------------|
| `dimensions` | int | 1 | 1 or 2 |
| `grid_size` | int | 100 | Grid resolution |
| `steps` | int | 500 | Time steps |
| `wave_speed` | float | 1.0 | Wave propagation speed c |
| `dt` | float | 0.1 | Time step |

**Result:** `max_amplitude`, `final_field` (list or 2D list)

---

### `population_genetics`
Wright-Fisher model of genetic drift: allele frequency evolution in a finite population over many generations.

| Payload Field | Type | Default | Description |
|--------------|------|---------|-------------|
| `population_size` | int | 500 | Diploid population size |
| `generations` | int | 1,000 | Number of generations |
| `initial_allele_freq` | float | 0.5 | Starting allele frequency |
| `mutation_rate` | float | 0.001 | Per-allele mutation probability |
| `n_replicates` | int | 20 | Independent simulation runs |

**Result:** `final_mean_freq`, `final_std_freq`, `fixed_count`, `lost_count`, `history_sample`

---

### `epidemic_sir`
SIR or SEIR compartmental epidemic model integrated with RK4.

| Payload Field | Type | Default | Description |
|--------------|------|---------|-------------|
| `model` | str | "SIR" | `SIR` or `SEIR` |
| `population` | int | 10,000 | Total population |
| `initial_infected` | int | 10 | Initially infected |
| `initial_exposed` | int | 0 | Initially exposed (SEIR only) |
| `beta` | float | 0.3 | Transmission rate |
| `gamma` | float | 0.05 | Recovery rate |
| `sigma` | float | 0.1 | Incubation rate (SEIR only) |
| `steps` | int | 365 | Days to simulate |

**Result:** `peak_infected`, `total_recovered`, `attack_rate`, `S_history`, `I_history`, `R_history` (+ `E_history` for SEIR)

---

### `game_of_life`
Conway's Game of Life cellular automaton.

| Payload Field | Type | Default | Description |
|--------------|------|---------|-------------|
| `grid_size` | int | 100 | Grid resolution |
| `steps` | int | 500 | Evolution steps |
| `pattern` | str | "random" | `random`, `glider`, `blinker` |
| `initial_density` | float | 0.3 | Live cell density (random pattern only) |

**Result:** `initial_population`, `final_population`, `max_population`, `min_population`, `population_history`, `final_grid`

---

### `financial_risk_mc`
Portfolio risk via Monte Carlo: simulates return scenarios using correlated geometric Brownian motion, computes Value at Risk (VaR) and Conditional VaR (CVaR).

| Payload Field | Type | Default | Description |
|--------------|------|---------|-------------|
| `n_assets` | int | 10 | Number of assets |
| `n_scenarios` | int | 100,000 | MC scenario count |
| `horizon_days` | int | 252 | Time horizon (trading days) |
| `confidence` | float | 0.95 | Confidence level |
| `portfolio_value` | float | 1,000,000.0 | Portfolio value ($) |
| `weights` | float[] | equal | Asset weights |
| `volatilities` | float[] | 0.2 each | Annual volatilities |
| `correlations` | float[] | identity | Flattened correlation matrix |

**Result:** `VaR`, `CVaR`, `VaR_pct`, `CVaR_pct`, `mean_pnl`, `std_pnl`

---

## Quick Reference Table

| # | Task Name | Category | One-liner |
|---|-----------|----------|-----------|
| 1 | `monte_carlo_pi` | Monte Carlo | Estimates π via random point sampling |
| 2 | `option_pricing` | Monte Carlo | Black-Scholes European call option pricing |
| 3 | `random_walk` | Monte Carlo | N particles random walking in D dimensions |
| 4 | `monte_carlo_integration` | Monte Carlo | Integrates sin/cos/exp/etc over [a,b] |
| 5 | `heat_diffusion_1d` | Heat & Diffusion | 1D heat equation, finite differences |
| 6 | `heat_diffusion_2d` | Heat & Diffusion | 2D heat equation on square grid |
| 7 | `chemical_diffusion` | Heat & Diffusion | 2D chemical species diffusion |
| 8 | `population_spread` | Heat & Diffusion | Fisher-KPP population growth + diffusion |
| 9 | `matrix_multiply` | Linear Algebra | N×N matrix multiply benchmark |
| 10 | `eigenvalue_decomp` | Linear Algebra | Eigenvalues of random symmetric matrix |
| 11 | `svd_decomposition` | Linear Algebra | SVD of random M×N matrix |
| 12 | `pca_covariance` | Linear Algebra | PCA via covariance eigendecomposition |
| 13 | `projectile_motion` | Physics | Projectile with air drag (Euler) |
| 14 | `lotka_volterra` | Physics | Predator-prey ODEs (RK4) |
| 15 | `pendulum_motion` | Physics | Damped nonlinear pendulum (RK4) |
| 16 | `spring_mass` | Physics | Damped harmonic oscillator (RK4) |
| 17 | `fluid_advection` | Fluid & Network | Particle advection in 2D flow (RK4) |
| 18 | `network_spread` | Fluid & Network | SIR spread on random graph |
| 19 | `traffic_flow` | Fluid & Network | Nagel-Schreckenberg traffic CA |
| 20 | `forest_fire` | Fluid & Network | Stochastic forest-fire CA |
| 21 | `diffusion_reaction` | Additional | Gray-Scott Turing pattern formation |
| 22 | `quantum_well` | Additional | Schrödinger equation, finite square well |
| 23 | `brownian_motion` | Additional | Stochastic diffusion with MSD tracking |
| 24 | `heat_conduction_varying` | Additional | 1D heat with variable conductivity |
| 25 | `fractal_dla` | Additional | Diffusion-limited aggregation fractal |
| 26 | `wave_propagation` | Additional | 1D/2D wave equation |
| 27 | `population_genetics` | Additional | Wright-Fisher genetic drift |
| 28 | `epidemic_sir` | Additional | SIR/SEIR epidemic model |
| 29 | `game_of_life` | Additional | Conway's Game of Life |
| 30 | `financial_risk_mc` | Additional | Portfolio VaR/CVaR via Monte Carlo |
