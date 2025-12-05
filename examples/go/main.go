package main

import (
	"encoding/json"
	"fmt"
	"os"
	"runtime"
	"time"
)

type Result struct {
	Timestamp  string  `json:"timestamp"`
	GoVersion  string  `json:"goVersion"`
	Sum        int     `json:"sum"`
	Average    float64 `json:"average"`
	Message    string  `json:"message"`
}

func main() {
	fmt.Println("=== NanoGrid Go Function ===")
	fmt.Println("Starting execution...")

	// 환경 정보 출력
	fmt.Printf("Go version: %s\n", runtime.Version())
	fmt.Printf("OS/Arch: %s/%s\n", runtime.GOOS, runtime.GOARCH)
	wd, _ := os.Getwd()
	fmt.Printf("Working directory: %s\n", wd)

	// 간단한 계산
	numbers := make([]int, 1000)
	for i := 0; i < 1000; i++ {
		numbers[i] = i + 1
	}

	sum := 0
	for _, num := range numbers {
		sum += num
	}
	average := float64(sum) / float64(len(numbers))

	fmt.Println("\nCalculation results:")
	fmt.Printf("Sum: %d\n", sum)
	fmt.Printf("Average: %.2f\n", average)

	// 결과를 JSON 파일로 저장
	result := Result{
		Timestamp: time.Now().Format(time.RFC3339),
		GoVersion: runtime.Version(),
		Sum:       sum,
		Average:   average,
		Message:   "Function executed successfully!",
	}

	data, err := json.MarshalIndent(result, "", "  ")
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error marshaling JSON: %v\n", err)
		os.Exit(1)
	}

	err = os.WriteFile("output.json", data, 0644)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error writing file: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("\n✓ Output written to output.json")
	fmt.Println("\nExecution completed successfully!")
}

