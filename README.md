# Hybrid File Sharing

## Workflow

### 1. Before you start
1. Open the project in **VS Code** through Github Desktop.
2. Open the terminal and check which branch you're on:
   ```bash
   git status
   ```
   The first line shows your branch (e.g. `On branch server`).
3. Get the latest changes from your branch **and** from `main`:
   ```bash
   git pull
   git pull origin main
   ```
   - If it says `Already up to date.`, you're fine. Continue working.
   - If it lists changed files, the latest merges were pulled in. Continue working.

   > ⚠️ `git pull` alone only updates the branch you're on. Always run `git pull origin main` too, or you won't get your teammate's merged work.

### 2. After you finish
1. Commit your work with a **title** and a **description**:
   ```bash
   git add .
   git commit -m "Title" -m "Description"
   ```
2. Push your branch:
   ```bash
   git push
   ```

### 3. Open a pull request (for new work)
Create a new pull request **from your branch into `main`**, titled:

```
Client/Server-Side Work (Week #<number>)
```

Example: `Client-Side Work (Week #1)`

Check the week-by-week plan in the project proposal to see which week your work belongs to.