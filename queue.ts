export class Queue<T> {
  private data: T[] = [];

  /**
   * Adds an element to the back of the queue.
   * @param element The element to add.
   */
  enqueue(element: T): void {
    this.data.push(element);
  }

  /**
   * Removes and returns the element from the front of the queue.
   * Returns undefined if the queue is empty.
   */
  dequeue(): T | undefined {
    if (this.isEmpty()) {
      return undefined;
    }
    return this.data.shift();
  }

  /**
   * Checks if the queue is empty.
   */
  isEmpty(): boolean {
    return this.data.length === 0;
  }

  /**
   * Returns the number of elements in the queue.
   */
  size(): number {
    return this.data.length;
  }
}