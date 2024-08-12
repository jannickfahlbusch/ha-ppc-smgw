package main

import (
	"crypto/tls"
	"fmt"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"strings"
)

func main() {
	// myTransport := &DumpTransport{
	// 	&http.Transport{
	// 		TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
	// 	},
	// }
	insecureTransport := &http.Transport{
		/*Dial: (&net.Dialer{
			Timeout:   30 * time.Second,
			KeepAlive: 30 * time.Second,
		}).Dial,*/
		TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
		//TLSHandshakeTimeout: 10 * time.Second,
	}

	proxy := &httputil.ReverseProxy{
		Rewrite: func(pr *httputil.ProxyRequest) {
			url, _ := url.Parse("https://192.168.178.200/")

			pr.SetURL(url)
		},
		ModifyResponse: func(pr *http.Response) error {
			setCookie := pr.Header.Get("Set-Cookie")
			if setCookie != "" {
				log.Println("Allowing Session Cookie to be served over insecure connection")
				newSetCookie := strings.Replace(setCookie, ";secure", "", -1)
				pr.Header.Set("Set-Cookie", newSetCookie)
			}

			return nil

		},
		Transport: insecureTransport,
	}

	http.Handle("/", &ProxyHandler{proxy})
	err := http.ListenAndServe(":8080", nil)
	if err != nil {
		panic(err)
	}
}

type ProxyHandler struct {
	p *httputil.ReverseProxy
}

func (ph *ProxyHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	log.Printf("Request received, proxing path %s (Method %s)\n", r.URL.Path, r.Method)
	ph.p.ServeHTTP(w, r)
}

type DumpTransport struct {
	r http.RoundTripper
}

func (d *DumpTransport) RoundTrip(h *http.Request) (*http.Response, error) {
	dump, _ := httputil.DumpRequestOut(h, true)
	fmt.Printf("****REQUEST****\n%s\n", dump)
	resp, err := d.r.RoundTrip(h)
	dump, _ = httputil.DumpResponse(resp, true)
	fmt.Printf("****RESPONSE****\n%s\n****************\n\n", dump)
	return resp, err
}
