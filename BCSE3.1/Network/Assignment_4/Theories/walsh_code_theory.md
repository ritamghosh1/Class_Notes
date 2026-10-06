# Walsh-Hadamard Code Module Theory — `walsh.py`

> **File**: `walsh.py`  
> **Class**: `WalshCodeGenerator`  
> **Layer**: Mathematical foundations & spreading code generation  

---

## 1. Mathematical Foundations

### 1.1 Hadamard Matrices
A **Hadamard matrix** $H_N$ of dimension $N$ is a square matrix whose entries are either $+1$ or $-1$, such that the row vectors (and column vectors) are mutually orthogonal.

The defining algebraic condition is:
$$H_N \cdot H_N^T = N \cdot I_N$$
where $I_N$ is the $N \times N$ identity matrix.

### 1.2 Sylvester's Recursive Construction
Sylvester demonstrated in 1867 that if $H_N$ is a Hadamard matrix of order $N$, then:
$$H_{2N} = \begin{bmatrix} H_N & H_N \\ H_N & -H_N \end{bmatrix} = \begin{bmatrix} 1 & 1 \\ 1 & -1 \end{bmatrix} \otimes H_N$$
where $\otimes$ denotes the Kronecker tensor product.

Starting from the scalar seed $H_1 = [1]$:

```
H_1 = [1]

H_2 = [ [ 1,  1 ],
        [ 1, -1 ] ]

H_4 = [ [ 1,  1,  1,  1 ],
        [ 1, -1,  1, -1 ],
        [ 1,  1, -1, -1 ],
        [ 1, -1, -1,  1 ] ]

H_8 = [ [ 1,  1,  1,  1,  1,  1,  1,  1 ],
        [ 1, -1,  1, -1,  1, -1,  1, -1 ],
        [ 1,  1, -1, -1,  1,  1, -1, -1 ],
        [ 1, -1, -1,  1,  1, -1, -1,  1 ],
        [ 1,  1,  1,  1, -1, -1, -1, -1 ],
        [ 1, -1,  1, -1, -1,  1, -1,  1 ],
        [ 1,  1, -1, -1, -1, -1,  1,  1 ],
        [ 1, -1, -1,  1, -1,  1,  1, -1 ] ]
```

---

## 2. Key Properties of Walsh-Hadamard Codes

### 2.1 Mutual Orthogonality
Let $W_i$ and $W_j$ represent rows $i$ and $j$ of matrix $H_N$.
The discrete inner product is defined as:
$$\langle W_i, W_j \rangle = W_i \cdot W_j = \sum_{k=0}^{N-1} W_i[k] \cdot W_j[k]$$

The orthogonality property states:
$$W_i \cdot W_j = \begin{cases}
N, & \text{if } i = j \quad \text{(Auto-correlation at zero lag)} \\
0, & \text{if } i \neq j \quad \text{(Cross-correlation at zero lag)}
\end{cases}$$

### 2.2 Gramian Matrix Verification
The Gramian matrix $G = H_N \cdot H_N^T$ encapsulates all pairwise inner products:
$$G_{ij} = W_i \cdot W_j$$
For perfect mutual orthogonality:
$$G = \begin{bmatrix}
N & 0 & \cdots & 0 \\
0 & N & \cdots & 0 \\
\vdots & \vdots & \ddots & \vdots \\
0 & 0 & \cdots & N
\end{bmatrix} = N \cdot I_N$$

### 2.3 Dimension Constraints
Sylvester's construction requires $N$ to be an integer power of two:
$$N = 2^k, \quad k \in \{1, 2, 3, \dots\}$$
For an arbitrary number of stations $n$, the system computes:
$$N = 2^{\lceil \log_2(n) \rceil}$$
For example:
- $n = 2 \implies N = 2$
- $n = 3 \implies N = 4$
- $n = 4 \implies N = 4$
- $n = 5 \dots 8 \implies N = 8$

---

## 3. Implementation Details in `walsh.py`

### 3.1 Class Architecture
```python
class WalshCodeGenerator:
    @staticmethod
    def next_power_of_two(n: int) -> int: ...
    
    @classmethod
    def generate_hadamard_matrix(cls, dimension: int) -> np.ndarray: ...
    
    @classmethod
    def get_walsh_set(cls, num_stations: int) -> tuple[np.ndarray, int]: ...
    
    @classmethod
    def get_code_for_station(cls, station_id: int, num_stations: int) -> np.ndarray: ...
    
    @classmethod
    def verify_orthogonality(cls, hadamard_matrix: np.ndarray) -> tuple[bool, np.ndarray]: ...
    
    @staticmethod
    def format_code(code: np.ndarray) -> str: ...
```

### 3.2 Algorithmic Efficiency
- Generating $H_N$ requires $k = \log_2(N)$ recursive block doublings.
- Computational time complexity: $O(N^2)$ to populate the matrix.
- Verification time complexity: $O(N^3)$ matrix multiplication via optimized BLAS (`np.dot`).
- Memory footprint: $N \times N \times 4$ bytes (less than $16 \text{ KB}$ for $N=64$).
