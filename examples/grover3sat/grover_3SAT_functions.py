from qibo import gates
from qibo.models import Circuit
import numpy as np

def bitstring(bits):
    return ''.join(str(int(b)) for b in bits)
    
def read_file(file_name):
    """Collect data from .tex file that characterizes the problem instance
    Args:
        file_name (str): name of the file that contains the instance information. Available
            in \data are examples for instances with 4, 8, 10, 12 and 16 qubits.
        
    Returns:
        control (list): important parameters of the instance. 
            [number of qubits, number of clauses, number of ones in the solution]
        solution (list): list of the correct outputs of the instance for testing.
        clauses (list): list of all clauses, with the qubits each clause acts upon.
    """
    file = open('data/{}'.format(file_name), 'r')
    control = list(map(int, file.readline().split()))
    solution = list(map(str, file.readline().split()))
    clauses = []
    for i in range(control[1]):
        clauses.append(list(map(int, file.readline().split())))
    return control, solution, clauses

def create_qc(qubits, clause_num):
    """Create the quantum circuit necessary to solve the problem. 
    Args:
        qubits (int): qubits needed to encode the problem.
        clause_num (int): number of clauses of the problem.
        
    """
    q = [i for i in range(qubits)]
    ancilla = qubits
    c = [i+qubits+1 for i in range(clause_num)]
    circuit = Circuit(qubits+clause_num+1)
    return q, c, ancilla, circuit

def start_grover(q, ancilla):
    """Generator that performs the starting step in Grover's search algorithm.
    Args:
        q (list): quantum register that encodes the problem.
        ancilla (int): Grover ancillary qubit. 
        
    """
    yield gates.X(ancilla)
    yield gates.H(ancilla)
    for i in q:
        yield gates.H(i)

def oracle(q, c, ancilla, clauses):
    """Generator that acts as the oracle for a 3SAT problem. Changes the sign of the amplitude of the quantum
    states that encode the solution.
    Args:
        q (list): quantum register that encodes the problem.
        c (list): quantum register that that records the satisfies clauses.
        ancilla (int): Grover ancillary qubit. Used to change the sign of the
            correct amplitudes.
        clauses (list): list of all clauses, with the qubits each clause acts upon.
        
    """
    k = 0
    for clause in clauses:
        yield gates.CNOT(q[clause[0]-1], c[k])
        yield gates.CNOT(q[clause[1]-1], c[k])
        yield gates.CNOT(q[clause[2]-1], c[k])
        yield gates.X(c[k]).controlled_by(q[clause[0]-1], q[clause[1]-1], q[clause[2]-1])
        k += 1
    yield gates.X(ancilla).controlled_by(*c)
    k = 0
    for clause in clauses:
        yield gates.CNOT(q[clause[0]-1], c[k])
        yield gates.CNOT(q[clause[1]-1], c[k])
        yield gates.CNOT(q[clause[2]-1], c[k])
        yield gates.X(c[k]).controlled_by(q[clause[0]-1], q[clause[1]-1], q[clause[2]-1])
        k += 1
        
def diffuser(q):
    """Generator that performs the inversion over the average step in Grover's search algorithm.
    Args:
        q (list): quantum register that encodes the problem.
        
    """
    for i in q:
        yield gates.H(i)
        yield gates.X(i)
    yield gates.H(q[0])
    yield gates.X(q[0]).controlled_by(*q[1:len(q)])
    yield gates.H(q[0])
    for i in q:
        yield gates.X(i)
        yield gates.H(i)
        
def grover(circuit, q, c, ancilla, clauses, steps):
    """Generator that performs the inversion over the average step in Grover's search algorithm.
    Args:
        circuit (Circuit):
        q (list): quantum register that encodes the problem.
        c (list): quantum register that that records the satisfies clauses.
        ancilla (int): Grover ancillary qubit.
        clauses (list): list of all clauses, with the qubits each clause acts upon.
        steps (int): number of times the oracle+diffuser operators have to be applied
            in order to find the solution. Grover's search algorihtm dictates O(sqrt(2**qubits)).
            
    Returns:
        circuit (Circuit): circuit with the full grover algorithm applied.
        
    """
    circuit.add(start_grover(q, ancilla))
    for i in range(steps):
        circuit.add(oracle(q, c, ancilla, clauses))
        circuit.add(diffuser(q))
    circuit.add(gates.M(*(q), register_name='result'))
    return circuit
