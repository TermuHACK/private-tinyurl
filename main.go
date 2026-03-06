package main

import (
 "database/sql"
 "fmt"
 "log"
 "net/http"
 "os"

 "golang.org/x/crypto/bcrypt"
 _ "github.com/lib/pq"
)

var db *sql.DB

func initDB() {

 query := `
 CREATE TABLE IF NOT EXISTS links (
  id SERIAL PRIMARY KEY,
  code TEXT UNIQUE NOT NULL,
  target_url TEXT NOT NULL,
  password_hash TEXT NOT NULL
 );
 `

 _, err := db.Exec(query)
 if err != nil {
  log.Fatal("table create error:", err)
 }
}

func loginPage(w http.ResponseWriter, r *http.Request) {

 code := r.URL.Path[1:]

 if code == "" {
  w.Write([]byte("OK"))
  return
 }

 html := fmt.Sprintf(`
 <html>
 <body>
 <h2>Access %s</h2>
 <form method="POST" action="/auth/%s">
 <input type="password" name="password" placeholder="password"/>
 <button type="submit">Login</button>
 </form>
 </body>
 </html>
 `, code, code)

 w.Write([]byte(html))
}

func auth(w http.ResponseWriter, r *http.Request) {

 code := r.URL.Path[len("/auth/"):]

 password := r.FormValue("password")

 var hash string
 var url string

 err := db.QueryRow(
  "SELECT password_hash,target_url FROM links WHERE code=$1",
  code,
 ).Scan(&hash, &url)

 if err != nil {
  http.NotFound(w, r)
  return
 }

 err = bcrypt.CompareHashAndPassword([]byte(hash), []byte(password))

 if err != nil {
  http.Error(w, "wrong password", 403)
  return
 }

 http.Redirect(w, r, url, 302)
}

func main() {

 dbUrl := os.Getenv("DB_URL")
 if dbUrl == "" {
  log.Fatal("DB_URL not set")
 }

 var err error
 db, err = sql.Open("postgres", dbUrl)
 if err != nil {
  log.Fatal(err)
 }

 initDB()

 http.HandleFunc("/auth/", auth)
 http.HandleFunc("/", loginPage)

 log.Println("server started :8080")
 http.ListenAndServe(":8080", nil)
}
