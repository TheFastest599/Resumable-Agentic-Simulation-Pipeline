# Example Chat Queries

---

Run 5 independent Monte Carlo π simulations with 2 million samples each.

Estimate π with 1 million iterations, then once that's done run a 512x512 matrix multiply.

Run a random walk with 10000 steps, 100 particles in 2D, and at the same time run heat diffusion on a 100-point 1D grid for 500 steps.

Price a European call option: stock at 100, strike 105, 1 year to expiry, 5% risk-free rate, 20% volatility, 500k simulations.

Simulate a pendulum with length 1.5m, damping 0.05, starting at 30 degrees, for 2000 steps.

Run the SIR epidemic model with 100000 people, infection rate 0.3, recovery rate 0.05, for 365 steps. When it finishes, run the SEIR version with the same parameters.

Run all four heat simulations in parallel: 1D diffusion, 2D diffusion, chemical diffusion, and population spread — all on a 100-point or 50x50 grid.

Do a full linear algebra benchmark: matrix multiply at size 512, eigenvalue decomp at size 256, SVD on 512x256, and PCA on 2000 samples with 100 features.

Simulate Brownian motion for 1000 particles over 5000 steps in 3D with diffusion coefficient 0.3.

Run a portfolio risk Monte Carlo with 10 assets, 50000 scenarios, 30-day horizon, 99% confidence.

Run the Gray-Scott reaction-diffusion on a 128x128 grid for 2000 steps with f=0.055, k=0.062. After it finishes, run the wave propagation simulation on the same grid size.

Run the Game of Life on a 200x200 grid with a glider pattern for 300 steps. Simultaneously run the forest fire model on a 150x150 grid with 60% tree density.

Check the status of all jobs from this conversation.

What happened to job abc123?
