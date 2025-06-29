import { exec } from 'node:child_process';
import util from 'node:util'
import { decodeHTML } from 'entities';

/**
 * Interleaves an arbitrary number of arrays (N arrays) with randomness.
 * Elements are picked randomly from any non-empty array until all arrays are exhausted.
 *
 * @template T The type of elements in the arrays.
 * @param {...T[][]} arrays An arbitrary number of arrays to interleave.
 * @returns {T[]} A new array with elements interleaved from all input arrays.
 */
export function interleaveArrays<T>(...arrays: T[][]): T[] {
  const result: T[] = [];
  // An array to keep track of the current index for each input array
  const pointers = new Array(arrays.length).fill(0);

  // Loop as long as there's at least one array with remaining elements
  while (true) {
    const availableIndices: number[] = [];

    // Find which arrays still have elements to contribute
    for (let i = 0; i < arrays.length; i++) {
      if (pointers[i] < arrays[i].length) {
        availableIndices.push(i);
      }
    }

    // If no arrays have elements left, break the loop
    if (availableIndices.length === 0) {
      break;
    }

    // Randomly select one of the available arrays
    const randomIndex = Math.floor(Math.random() * availableIndices.length);
    const selectedArrayIndex = availableIndices[randomIndex];

    // Push the element from the selected array to the result
    result.push(arrays[selectedArrayIndex][pointers[selectedArrayIndex]]);

    // Increment the pointer for the array from which an element was taken
    pointers[selectedArrayIndex]++;
  }

  return result;
}


export function getRandomElement<T>(list: T[]): T {
  const randomIndex = Math.floor(Math.random() * list.length);
  return list[randomIndex]!;
}

export const execPromise = util.promisify(exec);

export function stripHtml(str: string): string {
  str = str.replace(/([^\n])<\/?(h|br|p|ul|ol|li|blockquote|section|table|tr|div)(?:.|\n)*?>([^\n])/gm, '$1\n$3')
  str = str.replace(/<(?:.|\n)*?>/gm, '');
  return decodeHTML(str).trim();
}

export function delay(ms: number): Promise<void> {
    return new Promise( resolve => setTimeout(resolve, ms) );
}