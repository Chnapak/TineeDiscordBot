Short answer: what you have so far is a nice, well-motivated *setup*, but it’s not yet a rigorous “proof” of anything. Mathematically, there are some imprecisions and missing definitions you’ll want to clean up before you start proving the real results about equal entropies and counting distinct entropy values. 

I’ll go through:

1. Issues with notation / accuracy in what you have now
2. How to make the “When are entropies equal?” part genuinely rigorous
3. A concrete outline for how the paper could continue

---

## 1. Notation and mathematical accuracy

I’ll comment in roughly the order things appear.

### 1.1 Wyckoff positions and observables

Conceptually this part is fine, but you should be explicit about:

* What exactly is the “observable value” used in the entropy:

  * Is it always multiplicity?
  * Always arity?
  * Or do you choose some function of the pair ((m,a)), e.g. (f(m,a)=m), or (m a), or something else?

Right now you say you may use multiplicity, arity, or the pair ((m,a)). For entropy you *must* have a real, positive number attached to each selected site. So define a function:

[
w: \text{(Wyckoff positions)} \to (0,\infty),
]

and say that the “observable” you use for entropy is (w). Then:

* Multiplicity case: (w(p) = \text{mult}(p)).
* Arity case: (w(p) = \text{arity}(p)).
* Pair case: choose (and justify!) something like (w(p) = \alpha,\text{mult}(p)+\beta,\text{arity}(p)) or (w(p) = \text{mult}(p)\cdot g(\text{arity}(p))), etc.

Without this, your probability distribution is a bit mysterious.

---

### 1.2 “Reusable” vs “limited” sets (naming bug)

You write (paraphrasing):

> we separate the catalogue into two classes:
> (1) those constrained to a single independent occurrence
> (2) those that may be chosen repeatedly
> I call the former set the reusable set and the latter the limited set.

That’s backwards from the English meaning:

* “Reusable” should be the ones you can choose *repeatedly*.
* “Limited” should be the ones constrained to a single occurrence.

You should either swap the names or the description. Right now it’s self-contradictory and will confuse readers.

Also, it would help to give the sets actual symbols, e.g.

* (L) for limited sites (at most once),
* (R) for reusable sites (arbitrary multiplicity).

and then define formally what a “selection” is in terms of (L) and (R).

---

### 1.3 From observables to a probability distribution

You say:

> For a selection of (n) sites we transform these values into a probability distribution.

This needs an explicit formula. Something like:

* Let the selection be (M = {s_1,\dots,s_n}) (multiset).
* Let (x_i = w(s_i) > 0) be your observable value.
* Define

[
p_i = \frac{x_i}{\sum_{j=1}^n x_j}, \quad i=1,\dots,n.
]

Then (\mathbf{p} = (p_1,\dots,p_n)) is a probability distribution on (n) points (and you can note that if some (x_i = 0) you need a special convention, so better just assume (x_i>0)).

And then:

[
H(\mathbf{p}) = -\sum_{i=1}^n p_i \log p_i
]

with a choice of log base (base (2) or (e)), which you should state once.

Right now these formulas are *implicitly* there, but not written down. For a mathematical paper, they should be fully explicit.

---

### 1.4 The universe (U) and subset (A)

You write:

> Let (U) be the universe of all possible selections of whole numbers that can be repeated. (A \subseteq U) is the selections actually allowed by our reusable/limited sets.

and then:

> So if a property of a selection holds in the universal set, it can apply to its subsets.

A few issues:

1. At the beginning you talked about Wyckoff positions / observables, which might be e.g. integers, or ordered pairs ((m,a)), not just “whole numbers”. So better say:

   > Let (S) be the set of all possible observable values (e.g. multiplicities, arities, or ordered pairs).
   > Let (U) be the set of all finite multisets of elements of (S).
   > Let (A\subseteq U) be the subset of multisets that respect the reusable/limited constraints.

2. The sentence “if a property holds in the universal set, it holds in any subset” is true but trivial and slightly misleading.

   You really mean: if we prove a statement “For *every* selection in (U), property (P) holds”, then in particular it holds for every selection in the subset (A). That’s fine, but you don’t need to emphasize it as if it were a new idea; you can just say:

   > We will first formulate results for arbitrary selections in (U); all such results automatically apply to the more constrained set (A).

---

### 1.5 Representing a multiset by a vector

You say:

> Given a multiset (M) of size (n), we represent it by an ordered vector whose entries are the elements of (M), listed in nondecreasing order according to (\preceq). … It essentially forms a partially ordered set, but for the sake of the question, I prefer to use an ordered vector instead. Afterwards we transform the vector into a probability distribution.

Here are the issues:

1. **Define (\preceq).**
   You need to specify what order you are using on your observable set (S). If observables are just positive reals, you can use the usual (\le). If they are pairs ((m,a)), you need to say lexicographic order or some other consistent rule.

2. **Partial vs total order.**
   Sorting a vector “in nondecreasing order” implicitly requires a *total* order. If your order is genuinely only partial, there may be no way to sort all elements linearly.

   So either:

   * declare that (\preceq) is a total order (e.g. lexicographic on (\mathbb{N}^2)), or
   * don’t talk about sorted vectors at all; just treat the probability vector as an unordered multiset (since entropy is symmetric).

3. **Missing function definition.**
   You say “Define … to be a vector of length (n) containing all elements of (M)”, but in the version I see the actual function symbol is missing. It should be something like:

   [
   v(M) = (x_1,\dots,x_n),
   ]
   where ((x_1,\dots,x_n)) is the nondecreasing list of elements in (M).

   Then your distribution is (p(M) = v(M) / \sum_i v(M)_i).

4. **Link to entropy.**
   It would be clearer to define a *composition* of maps:

   [
   M ;\xmapsto{v}; v(M) ;\xmapsto{\text{normalize}}; p(M) ;\xmapsto{H}; H(p(M)).
   ]

   Then your fundamental object is the map (H\circ p \circ v), from multisets to real numbers.

---

## 2. Is the “proof” spotless?

Right now, what you have under “When are entropies equal?” is still **preliminary setup**, not really a proof of a theorem. You haven’t yet stated a precise result like:

> Theorem: Two selections (M,N \in U) satisfy (H(M)=H(N)) *if and only if* …

or even:

> Proposition: The following operations preserve entropy: …

To turn this into a real mathematical proof section, I’d suggest something like:

### 2.1 Define the equivalence relation

Let:

* (M) be a finite multiset of observables,
* (v(M)) the corresponding vector of positive observables,
* (p(M)) the normalized probability vector,
* (H(M) = H(p(M))) the entropy.

Define an equivalence relation on selections:

[
M \sim N \quad\Longleftrightarrow\quad H(M) = H(N).
]

Your first question “When are entropies equal?” is precisely: **describe or partially characterize the equivalence classes of (\sim).**

### 2.2 Immediately provable entropy-invariance facts

These are the kinds of statements you *can* prove cleanly and early:

1. **Permutation invariance**
   If (N) is obtained from (M) just by permuting the order of entries in (v(M)), then (H(M)=H(N)).

   *Proof sketch:* (p(M)) and (p(N)) differ only by permutation, and Shannon entropy is symmetric in its arguments.

2. **Global scaling invariance**
   Let (v(M) = (x_1,\dots,x_n)) and let (v'(M)) be ((\lambda x_1,\dots,\lambda x_n)) for some (\lambda>0). Then

   [
   p_i' = \frac{\lambda x_i}{\sum_j \lambda x_j} = \frac{x_i}{\sum_j x_j} = p_i,
   ]

   so (H(M) = H(M')).

   In your own wording from the intro: any two selections whose observable vectors are positive multiples of each other give exactly the same distribution, hence the same entropy.

3. **Coarsening by merging equal probabilities** (optional but neat)
   Suppose a selection has some observable value repeated (k) times; you can consider a “coarse-grained” object where those (k) sites are grouped into one probability (kp), etc. There are clean inequalities for entropy under such coarse-graining.

You can formalize these as **lemmas**, each with a short proof.

### 2.3 Nontrivial equal-entropy examples

An important mathematical observation (and something the paper can exploit) is:

* For fixed dimension (n), the simplex of all probability vectors is ((n-1))-dimensional.
* Shannon entropy is a continuous scalar function on that simplex.
* Level sets ({p : H(p) = c}) are typically ((n-2))-dimensional manifolds—so there is a *continuum* of different distributions with the same entropy.

In your discrete setting (probabilities with rational entries coming from integers in your reusable/limited sets), that means:

* There are **many, many** different multisets with identical entropy, far beyond simple scaling or permutation symmetries.

You probably won’t classify all such degeneracies (that’s very hard), but you can:

* Prove the simple invariances rigorously.
* Give concrete examples of distinct integer vectors ((x_i)) and ((y_i)) that generate different probability vectors but the same entropy numerically.
* Then focus on counting / characterizing entropy values *within the combinatorial constraints* of your reusable/limited sets.

So: the current text doesn’t contain errors in the *ideas*, but it does lack explicit definitions and theorems. It needs to be upgraded from “informal discussion” to “formal statements + proofs”.

---

## 3. How might the paper continue?

Here’s a reasonable roadmap from where you are:

### Section 2: Formal setup

1. **Observables and selections**

   * Define the observable space (S) and weighting function (w: S \to (0,\infty)).
   * Define the limited set (L\subseteq S) and reusable set (R\subseteq S).
   * Define a “selection” as a multiset (M) with:

     * any element of (L) appearing at most once,
     * elements of (R) with arbitrary multiplicity.

2. **From selection to entropy**

   * Define (v(M)), (p(M)), and (H(M)) rigorously, as above.
   * Note symmetry under permutation and scaling.

This becomes your “Preliminaries” section.

---

### Section 3: Equality of entropies

Goal: tackle your Question 1 (“When are entropies equal?”).

Possible structure:

1. **Entropy-preserving operations**

   * Prove lemmas for permutation and scaling invariance, and any other simple operations (e.g. re-labelling observables with equal weights).
   * Show that these generate a subgroup of transformations under which (H) is invariant.

2. **Equivalence classes under those operations**

   * Define a *coarser* equivalence (\approx) given by “same normalized observable vector up to permutation”; then (\approx) implies (\sim).
   * Your combinatorial counting can first reduce modulo (\approx), then worry about further degeneracies of (\sim).

3. **Nontrivial degeneracies**

   * Provide explicit examples where two non-equivalent normalized vectors still have equal entropies.
   * Discuss how common such coincidences are (e.g. measure-zero in a continuous sense, but infinitely many in your discrete set).

This section doesn’t need a full classification, but it should clearly separate:

* Trivial reasons for equal entropy (symmetry, scaling).
* Nontrivial coincidences.

---

### Section 4: Counting distinct entropy values

This addresses your Questions 2 and 3.

1. **General counting framework**

   * Fix finite sets (L) and (R), and maybe a max selection size (n).
   * Describe the set of all integer vectors consistent with these constraints.
   * Explain that each such vector maps to some entropy value (H), and you’re interested in the cardinality of the image.

2. **Upper and lower bounds**

   * Basic bounds: number of distinct entropies is at most number of allowed selections (trivial), but you can often get better combinatorial bounds.
   * Possible linkage to integer partition/composition counts if (R) and (L) have simple structure.

3. **Special cases with simpler formulas**

   * Example: (R={1}), (L=\emptyset): all observables equal. Then every selection gives the *same* probability vector, so there is exactly 1 entropy value.
   * Example: small (R) like ({1,2}), with varying selection sizes—this might be tractable by hand and illustrative.
   * If you can, find closed forms or asymptotics for specific families of (R,L).

---

### Section 5: Crystallographic applications / data

To tie back to the crystallography motivation:

1. **Real space-group datasets**

   * Take actual lists of Wyckoff positions for selected space groups.
   * Compute the entropies for the valid physical selections.
   * Show plots / histograms of entropy values.

2. **Interpretation**

   * Does higher entropy correlate with structural “complexity” in a meaningful way (e.g., number of independent parameters, degrees of positional disorder, etc.)?

This section is where your mathematical framework pays off for the domain audience.

---

## 4. Summary

* Mathematically, your **ideas** are solid, but several key definitions are only implicit or slightly inconsistent (especially reusable vs limited, the use of “whole numbers”, and the ordering/representation of multisets).
* There is not yet a full “proof” to audit; instead, you have the opening of what will become a Preliminaries + first theorem section.
* To proceed, I’d recommend:

  1. Write down the exact maps (M \mapsto v(M) \mapsto p(M) \mapsto H(M)).
  2. Clean up the set notation ((U, A, L, R, S)) and fix the naming swap.
  3. State and prove a few clear lemmas about entropy invariance (permutation, scaling, maybe simple coarse-grainings).
  4. Then move on to counting distinct entropies for simple toy choices of (L) and (R).

If you’d like, I can help you rewrite one of the sections (say, the “When are entropies equal?” part) into a fully rigorous theorem-plus-proof style text.
